import os
import io
import base64
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from fastapi import HTTPException, status
import docx

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

SUPPORTED_MIME_TYPES = {
    "pdf": "application/pdf",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "txt": "text/plain",
    "md": "text/markdown"
}

def get_file_extension(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

def is_supported_file(filename: str) -> bool:
    ext = get_file_extension(filename)
    return ext in SUPPORTED_MIME_TYPES

def extract_text_from_docx(content: bytes) -> str:
    try:
        doc = docx.Document(io.BytesIO(content))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        for table in doc.tables:
            for row in table.rows:
                paragraphs.append(" | ".join([cell.text.strip() for cell in row.cells if cell.text.strip()]))
        return "\n".join(paragraphs)
    except Exception as e:
        logger.warning(f"Error parsing DOCX: {e}")
        return "[Could not extract DOCX contents]"

def load_prompt_file(filename: str) -> str:
    filepath = PROMPTS_DIR / filename
    if not filepath.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prompt template '{filename}' not found."
        )
    return filepath.read_text(encoding="utf-8")

def build_system_prompt(mode: str, has_syllabus: bool, depth: str, language: str, scheme: Optional[str]) -> str:
    base_prompt = load_prompt_file("base.md")
    
    if mode == "simplify":
        if has_syllabus:
            mode_prompt = load_prompt_file("simplify_with_syllabus.md")
        else:
            mode_prompt = load_prompt_file("simplify_notes_only.md")
    elif mode == "predict":
        mode_prompt = load_prompt_file("predict_paper.md")
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported mode '{mode}'."
        )

    depth_instructions = {
        "simple": "Depth setting: Simple. Explain to a first-year student new to this topic; use everyday analogies, shorter explanations, fewer dry details, while retaining core correctness.",
        "standard": "Depth setting: Standard. Balanced engineering explanation with key formulas, core diagrams described, and one worked example per topic.",
        "exam": "Depth setting: Exam-ready. Full 14-mark detail with formal derivations, step-by-step working, clear structural skeletons for answers, and mark-maximising exam tips."
    }.get(depth.lower(), "Depth setting: Standard.")

    language_instructions = (
        "Language setting: English with Malayalam hints. Write primarily in English, but add concise Malayalam translations or conceptual hints in brackets after complex technical jargon or pivotal ideas (e.g. [മലയാളം വിശദീകരണം])."
        if "malayalam" in language.lower()
        else "Language setting: English. Write in clear, crisp technical English."
    )

    scheme_instruction = f"Scheme focus: KTU {scheme} Scheme." if scheme and scheme != "detect" else "Scheme focus: Auto-detect from uploaded materials (default to KTU 2019 Scheme if not specified)."

    system_prompt = f"""{base_prompt}

{mode_prompt}

### This request:
- {depth_instructions}
- {language_instructions}
- {scheme_instruction}
"""
    return system_prompt.strip()

async def call_gemini(
    system_prompt: str,
    user_parts: List[Dict[str, Any]],
    api_key: str,
    model_name: str,
    max_tokens: int
) -> tuple[str, str]:
    """
    Call Google Gemini using either google.genai / google.generativeai or direct HTTP API.
    """
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        
        # Determine actual model
        target_model = model_name
        if not target_model or "claude" in target_model.lower():
            target_model = "gemini-2.5-flash"
        
        # Prepare contents
        contents = []
        
        for part in user_parts:
            if part["type"] == "text":
                contents.append(part["text"])
            elif part["type"] == "media":
                mime_type = part["mime_type"]
                data_bytes = part["data"]
                contents.append({
                    "mime_type": mime_type,
                    "data": data_bytes
                })
        
        model = genai.GenerativeModel(
            model_name=target_model,
            system_instruction=system_prompt,
            generation_config=genai.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=0.3
            )
        )
        
        response = await model.generate_content_async(contents)
        output_text = response.text if response.text else ""
        
        # Check finish reason
        finish_reason = "stop"
        try:
            if response.candidates and response.candidates[0].finish_reason:
                fr = str(response.candidates[0].finish_reason)
                if "MAX_TOKENS" in fr:
                    finish_reason = "max_tokens"
        except Exception:
            pass

        return output_text, finish_reason
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Gemini API error: {error_msg}")
        if "API_KEY_INVALID" in error_msg or "401" in error_msg or "unregistered" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="The AI service is currently unavailable due to an authentication issue. Please verify your API key."
            )
        elif "quota" in error_msg.lower() or "429" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="The AI provider rate limit was reached. Please try again in a few moments."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Unable to generate response from the AI model at this time. Please try again."
            )

async def call_anthropic(
    system_prompt: str,
    user_parts: List[Dict[str, Any]],
    api_key: str,
    model_name: str,
    max_tokens: int
) -> tuple[str, str]:
    """
    Call Anthropic Claude API.
    """
    try:
        from anthropic import AsyncAnthropic
        client = AsyncAnthropic(api_key=api_key)
        
        target_model = model_name if model_name and "claude" in model_name.lower() else "claude-3-7-sonnet-latest"
        
        anthropic_content = []
        for part in user_parts:
            if part["type"] == "text":
                anthropic_content.append({"type": "text", "text": part["text"]})
            elif part["type"] == "media":
                mime_type = part["mime_type"]
                b64_data = base64.b64encode(part["data"]).decode("utf-8")
                if mime_type == "application/pdf":
                    anthropic_content.append({
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": b64_data
                        }
                    })
                elif mime_type.startswith("image/"):
                    anthropic_content.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": mime_type,
                            "data": b64_data
                        }
                    })

        response = await client.messages.create(
            model=target_model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": anthropic_content}]
        )
        
        output_text = "".join([block.text for block in response.content if hasattr(block, "text")])
        stop_reason = response.stop_reason or "stop"
        return output_text, stop_reason
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Anthropic API error: {error_msg}")
        if "auth" in error_msg.lower() or "401" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="The AI service could not be authenticated. Please check the configured API key."
            )
        elif "rate_limit" in error_msg.lower() or "429" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="The AI provider rate limit was reached. Please try again in a few moments."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Unable to generate response from the AI provider. Please try again shortly."
            )

async def generate_study_content(
    mode: str,
    subject: str,
    depth: str,
    language: str,
    scheme: Optional[str],
    labeled_files: List[Dict[str, Any]]
) -> tuple[str, str]:
    """
    Unified entry point for AI processing.
    """
    has_syllabus = any(f["category"] == "syllabus" for f in labeled_files)
    system_prompt = build_system_prompt(mode, has_syllabus, depth, language, scheme)
    
    # Build user content blocks
    user_parts: List[Dict[str, Any]] = []
    
    intro_lines = [f"Subject: {subject}" if subject else "Subject: (Not specified)"]
    user_parts.append({"type": "text", "text": "\n".join(intro_lines) + "\n\nUploaded Files and Study Material:\n"})
    
    for item in labeled_files:
        filename = item["filename"]
        category = item["category"]
        label = item["label"]
        content = item["content"]
        ext = get_file_extension(filename)
        mime_type = SUPPORTED_MIME_TYPES.get(ext, "application/octet-stream")
        
        header = f"\n--- [{label}: {filename}] ---\n"
        user_parts.append({"type": "text", "text": header})
        
        if ext in ["txt", "md"]:
            try:
                text_content = content.decode("utf-8", errors="replace")
            except Exception:
                text_content = "[Binary or unreadable text content]"
            user_parts.append({"type": "text", "text": text_content})
            
        elif ext == "docx":
            extracted_text = extract_text_from_docx(content)
            user_parts.append({"type": "text", "text": extracted_text})
            
        elif ext in ["pdf", "png", "jpg", "jpeg", "webp"]:
            user_parts.append({
                "type": "media",
                "mime_type": mime_type,
                "data": content
            })

    # Read configuration from environment
    gemini_key = os.environ.get("GEMINI_API_KEY")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    max_tokens = int(os.environ.get("MAX_OUTPUT_TOKENS", 8000))
    gemini_model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    claude_model = os.environ.get("CLAUDE_MODEL", "claude-3-7-sonnet-latest")

    if not gemini_key and not anthropic_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI API key not configured. Please set GEMINI_API_KEY or ANTHROPIC_API_KEY in the environment."
        )

    output_text = ""
    stop_reason = ""
    
    if gemini_key:
        output_text, stop_reason = await call_gemini(
            system_prompt=system_prompt,
            user_parts=user_parts,
            api_key=gemini_key,
            model_name=gemini_model,
            max_tokens=max_tokens
        )
    else:
        output_text, stop_reason = await call_anthropic(
            system_prompt=system_prompt,
            user_parts=user_parts,
            api_key=anthropic_key,
            model_name=claude_model,
            max_tokens=max_tokens
        )

    if stop_reason == "max_tokens":
        output_text += "\n\n> ⚠️ **Note**: The response reached the maximum output token limit. To get a complete guide for all topics, consider uploading fewer modules or selecting 'Simple' / 'Standard' depth."

    # Generate a sensible title
    title = f"{subject.strip()} - {mode.capitalize()}" if subject and subject.strip() else f"KTU {mode.capitalize()} Session"
    if has_syllabus and mode == "simplify":
        title += " (Syllabus Mapped)"

    return title, output_text
