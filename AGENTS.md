# AGENTS.md &bull; Engineering & Automation Guidelines

This document outlines architecture rules, testing commands, and operational boundaries for AI agents maintaining the Sutra codebase.

---

## 🛠️ Verification & Build Commands

### Backend Syntax & Compilation Verification
```bash
python -m py_compile backend/main.py backend/auth.py backend/db.py backend/ai.py
```

### Frontend Syntax Verification
```bash
node --check frontend/js/common.js
node --check frontend/js/landing.js
node --check frontend/js/app.js
```

### Starting the Application Server
```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 📌 Strict Rules & Invariants

### 1. Prompt File Isolation
- **DO NOT hardcode system prompts** inside Python code or frontend JavaScript.
- All AI behavior instructions and KTU schema prompts must reside exclusively in `prompts/*.md`:
  - `prompts/base.md`
  - `prompts/simplify_with_syllabus.md`
  - `prompts/simplify_notes_only.md`
  - `prompts/predict_paper.md`
- Prompt files are loaded dynamically from disk on each request so instructors and engineers can adjust instructions without server restarts.

### 2. API Contract Stability
- Keep the endpoints and response schemas stable:
  - `POST /api/auth/signup` $\to$ `{ token, name }`
  - `POST /api/auth/login` $\to$ `{ token, name }`
  - `GET /api/auth/me` $\to$ `{ id, name, email, usage: { used, limit } }`
  - `POST /api/process` $\to$ `{ id, title, output, usage: { used, limit } }`
  - `GET /api/history` $\to$ Array of `{ id, mode, subject, depth, language, scheme, title, created_at }`
  - `GET /api/history/{id}` $\to$ Full record with `output`
  - `DELETE /api/history/{id}` $\to$ `{ success: true, id }`

### 3. XSS Prevention & Safe DOM Handling
- **Never use `innerHTML` with unsanitized user inputs or file names.**
- User-supplied strings (filenames, subjects, names) must use `textContent` or HTML-escaped text.
- AI-generated Markdown output must be parsed and strictly sanitized via `DOMPurify.sanitize(...)` with MathML / KaTeX tags whitelisted.

### 4. Accessibility & Motion Preference
- The root `<html>` tag must have `.rm` (reduced motion) or `.anim` (standard motion) applied before first render.
- When `.rm` is active:
  - Scroll progress and pinned animations must immediately resolve to their final clean state.
  - Anime.js transitions and keyframes must be skipped or set to instantaneous completion.

### 5. Security & Credentials
- Never commit `.env`, `*.db`, or `*.db-journal` files.
- Passwords must always be hashed with `hashlib.scrypt` and a cryptographically random 16-byte salt, compared via constant-time `hmac.compare_digest`.
- API error handlers must return clean 502/503 HTTP status messages with actionable copy without ever exposing raw exception tracebacks or environment secrets.
