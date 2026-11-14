import os
import sys
from pathlib import Path
from typing import List, Literal, Optional
from urllib.parse import quote
from dotenv import load_dotenv

# Load .env file
load_dotenv()

from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import httpx

from backend.db import (
    get_today_usage,
    record_usage,
    save_history,
    list_history,
    get_history_item,
    delete_history_item,
)
from backend.auth import get_current_user
from backend.ai import generate_study_content, is_supported_file, get_file_extension

STORAGE_BUCKET = "sutra-uploads"


class StoredUpload(BaseModel):
    path: str
    filename: str
    category: Literal["notes", "syllabus", "past_questions"]


class StoredProcessRequest(BaseModel):
    mode: str
    subject: str = ""
    depth: str = "standard"
    language: str = "english"
    scheme: str = "detect"
    files: List[StoredUpload] = Field(default_factory=list)

app = FastAPI(title="Sutra API", description="AI Study Companion for KTU B.Tech Students (Supabase Auth & RLS)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DAILY_LIMIT = int(os.environ.get("DAILY_LIMIT", 10))
MAX_FILE_MB = int(os.environ.get("MAX_FILE_MB", 20))
MAX_FILE_BYTES = MAX_FILE_MB * 1024 * 1024

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")

# ----------------- CONFIG & USER PROFILE -----------------

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "Sutra API"}

@app.get("/api/config")
def get_client_config():
    """Provides public Supabase configuration for the frontend SDK."""
    return {
        "supabaseUrl": SUPABASE_URL,
        "supabaseAnonKey": SUPABASE_ANON_KEY
    }

@app.get("/api/auth/me")
def get_current_user_profile(user: dict = Depends(get_current_user)):
    used_today = get_today_usage(user["id"])
    return {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "usage": {
            "used": used_today,
            "limit": DAILY_LIMIT
        }
    }

# ----------------- PROCESS ENDPOINT -----------------

@app.post("/api/process")
async def process_study_request(
    mode: str = Form(...),
    subject: str = Form(""),
    depth: str = Form("standard"),
    language: str = Form("english"),
    scheme: str = Form("detect"),
    notes: List[UploadFile] = File(default=[]),
    syllabus: List[UploadFile] = File(default=[]),
    past_questions: List[UploadFile] = File(default=[]),
    user: dict = Depends(get_current_user)
):
    # Enforce daily limit
    used_today = get_today_usage(user["id"])
    if used_today >= DAILY_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"You have reached your daily limit of {DAILY_LIMIT} runs. Your quota resets at midnight UTC."
        )

    # Validate mode and required files
    mode = mode.lower().strip()
    if mode not in ["simplify", "predict"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mode must be either 'simplify' or 'predict'."
        )

    valid_notes = [f for f in notes if f.filename and f.size != 0]
    valid_syllabus = [f for f in syllabus if f.filename and f.size != 0]
    valid_past_questions = [f for f in past_questions if f.filename and f.size != 0]

    if mode == "simplify":
        if not valid_notes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Simplify mode requires at least one lecture notes file."
            )
    elif mode == "predict":
        if not valid_past_questions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Predict mode requires at least one previous year question paper."
            )
        if not valid_notes and not valid_syllabus:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Predict mode requires at least one lecture notes file OR syllabus document in addition to past papers."
            )

    # Process and validate all uploaded files
    labeled_files = []
    all_uploads = (
        [(f, "notes", "NOTES") for f in valid_notes] +
        [(f, "syllabus", "SYLLABUS") for f in valid_syllabus] +
        [(f, "past_questions", "PREVIOUS QUESTION PAPER") for f in valid_past_questions]
    )

    for upload_file, category, label in all_uploads:
        filename = upload_file.filename or "unknown"
        if not is_supported_file(filename):
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Unsupported file type '{filename}'. Accepted formats are PDF, DOCX, TXT, MD, PNG, JPG, JPEG, WEBP."
            )
        
        content = await upload_file.read()
        if len(content) > MAX_FILE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File '{filename}' exceeds the maximum allowed size of {MAX_FILE_MB}MB."
            )
        
        if len(content) == 0:
            continue
            
        labeled_files.append({
            "filename": filename,
            "category": category,
            "label": label,
            "content": content
        })

    if not labeled_files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No readable files were uploaded."
        )

    # Call AI Provider
    title, output = await generate_study_content(
        mode=mode,
        subject=subject,
        depth=depth,
        language=language,
        scheme=scheme,
        labeled_files=labeled_files
    )

    # Record usage and save history
    record_usage(user["id"])
    history_record = save_history(
        user_id=user["id"],
        mode=mode,
        subject=subject,
        depth=depth,
        language=language,
        scheme=scheme,
        title=title,
        output=output
    )

    new_usage = get_today_usage(user["id"])

    return {
        "id": history_record.get("id"),
        "title": title,
        "output": output,
        "usage": {
            "used": new_usage,
            "limit": DAILY_LIMIT
        }
    }


@app.post("/api/process-stored")
async def process_stored_study_request(
    payload: StoredProcessRequest,
    user: dict = Depends(get_current_user)
):
    """Process files staged directly in Supabase Storage to avoid Vercel's body limit."""
    used_today = get_today_usage(user["id"])
    if used_today >= DAILY_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"You have reached your daily limit of {DAILY_LIMIT} runs. Your quota resets at midnight UTC."
        )

    mode = payload.mode.lower().strip()
    if mode not in {"simplify", "predict"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mode must be either 'simplify' or 'predict'.")
    if mode == "simplify" and not any(item.category == "notes" for item in payload.files):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Simplify mode requires at least one lecture notes file.")
    if mode == "predict":
        if not any(item.category == "past_questions" for item in payload.files):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Predict mode requires at least one previous year question paper.")
        if not any(item.category in {"notes", "syllabus"} for item in payload.files):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Predict mode requires notes or a syllabus in addition to past papers.")

    supabase_url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    service_key = os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not supabase_url or not service_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase Storage is not configured. Set SUPABASE_URL and SUPABASE_SERVICE_KEY on the server."
        )

    owned_uploads = []
    for item in payload.files:
        segments = item.path.split("/")
        if len(segments) < 3 or segments[0] != str(user["id"]) or any(part in {"", ".", ".."} for part in segments):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="An uploaded file path is invalid or belongs to another user.")
        if not is_supported_file(item.filename):
            raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=f"Unsupported file type '{item.filename}'.")
        owned_uploads.append(item)

    if not owned_uploads:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No files were uploaded.")

    headers = {"apikey": service_key, "Authorization": f"Bearer {service_key}"}
    labeled_files = []
    labels = {"notes": "NOTES", "syllabus": "SYLLABUS", "past_questions": "PREVIOUS QUESTION PAPER"}

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            for item in owned_uploads:
                object_url = (
                    f"{supabase_url}/storage/v1/object/{STORAGE_BUCKET}/"
                    f"{quote(item.path, safe='/')}"
                )
                response = await client.get(object_url, headers=headers)
                if response.status_code == 404:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="An uploaded file expired. Please upload it again.")
                if response.status_code != 200:
                    raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Could not retrieve an uploaded file from Supabase Storage.")
                if len(response.content) > MAX_FILE_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File '{item.filename}' exceeds the maximum allowed size of {MAX_FILE_MB}MB."
                    )
                labeled_files.append({
                    "filename": item.filename,
                    "category": item.category,
                    "label": labels[item.category],
                    "content": response.content
                })

            title, output = await generate_study_content(
                mode=mode,
                subject=payload.subject,
                depth=payload.depth,
                language=payload.language,
                scheme=payload.scheme,
                labeled_files=labeled_files
            )
            record_usage(user["id"])
            history_record = save_history(
                user_id=user["id"],
                mode=mode,
                subject=payload.subject,
                depth=payload.depth,
                language=payload.language,
                scheme=payload.scheme,
                title=title,
                output=output
            )
            return {
                "id": history_record.get("id"),
                "title": title,
                "output": output,
                "usage": {"used": get_today_usage(user["id"]), "limit": DAILY_LIMIT}
            }
        finally:
            # Temporary study materials should not remain in storage after processing.
            for item in owned_uploads:
                object_url = (
                    f"{supabase_url}/storage/v1/object/{STORAGE_BUCKET}/"
                    f"{quote(item.path, safe='/')}"
                )
                try:
                    await client.delete(object_url, headers=headers)
                except httpx.HTTPError:
                    pass

# ----------------- HISTORY ENDPOINTS -----------------

@app.get("/api/history")
def get_history(user: dict = Depends(get_current_user)):
    return list_history(user["id"])

@app.get("/api/history/{history_id}")
def get_history_detail(history_id: int, user: dict = Depends(get_current_user)):
    item = get_history_item(user["id"], history_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Study session record not found."
        )
    return item

@app.delete("/api/history/{history_id}")
def delete_history(history_id: int, user: dict = Depends(get_current_user)):
    deleted = delete_history_item(user["id"], history_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Study session record not found or already removed."
        )
    return {"success": True, "id": history_id}

# ----------------- STATIC FILES & FRONTEND -----------------

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

if FRONTEND_DIR.exists():
    app.mount("/css", StaticFiles(directory=str(FRONTEND_DIR / "css")), name="css")
    app.mount("/js", StaticFiles(directory=str(FRONTEND_DIR / "js")), name="js")

@app.get("/")
def serve_index():
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return JSONResponse({"message": "Sutra API is active."})

@app.get("/app.html")
def serve_app():
    app_path = FRONTEND_DIR / "app.html"
    if app_path.exists():
        return FileResponse(str(app_path))
    return JSONResponse({"message": "Frontend app.html not found."}, status_code=404)
