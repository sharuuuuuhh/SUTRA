# Sutra &bull; KTU AI Study Companion (Supabase Auth & PostgreSQL)

Sutra is a production-grade AI study companion purpose-built for B.Tech students under APJ Abdul Kalam Technological University (KTU), Kerala. It transforms raw lecture PDFs, Word documents, text notes, and handwritten notebook scans into syllabus-aligned study guides, coverage audit matrices, and evidence-based predicted question papers.

---

## ⚡ Setup Guide: Supabase Auth & Google Login

Follow these step-by-step instructions to configure Google OAuth and Supabase PostgreSQL with Row Level Security (RLS).

### Step 1: Create a Supabase Project & Execute Database Schema
1. Go to [database.new](https://database.new) and create a new project on **Supabase**.
2. Once the project is created, open the **SQL Editor** from the left sidebar.
3. Open [`supabase_schema.sql`](file:///C:/Users/sharu/.gemini/antigravity-ide/scratch/sutra/supabase_schema.sql) in this repository, copy the entire SQL script, paste it into the Supabase SQL Editor, and click **Run**.
   - This creates the `history` and `usage_logs` tables.
   - It enables **Row Level Security (RLS)** ensuring users can only ever access their own study sessions.
4. Go to **Project Settings &rarr; API**:
   - Copy **Project URL** &rarr; set as `SUPABASE_URL` in `.env`.
   - Copy **Project API keys: `anon` `public`** &rarr; set as `SUPABASE_ANON_KEY` in `.env`.
   - Copy **Project API keys: `service_role` `secret`** &rarr; set as `SUPABASE_SERVICE_KEY` in `.env`.
   - (Optional) Copy **JWT Secret** &rarr; set as `SUPABASE_JWT_SECRET` in `.env`.

---

### Step 2: Configure Google Cloud OAuth 2.0
1. Open the [Google Cloud Console Credentials Page](https://console.cloud.google.com/apis/credentials).
2. Click **Create Credentials &rarr; OAuth client ID**.
3. Set **Application type** to **Web application**.
4. Set **Name** to `Sutra KTU Study Companion`.
5. Under **Authorized JavaScript origins**, add:
   - `http://localhost:8000`
   - `https://<your-project-ref>.supabase.co`
   - Your production domain (e.g. `https://sutra.app`)
6. Under **Authorized redirect URIs**, add your Supabase project callback URL:
   - `https://<your-project-ref>.supabase.co/auth/v1/callback`
7. Click **Create** and copy your **Client ID** and **Client Secret**.

---

### Step 3: Enable Google Provider in Supabase
1. In your Supabase Dashboard, navigate to **Authentication &rarr; Providers &rarr; Google**.
2. Toggle **Enable Google provider** to ON.
3. Paste the **Client ID** and **Client Secret** copied from Google Cloud Console.
4. Click **Save**.
5. Navigate to **Authentication &rarr; URL Configuration**:
   - Set **Site URL** to `http://localhost:8000`.
   - Add to **Redirect URLs**:
     - `http://localhost:8000/**`
     - `http://localhost:8000/app.html`
     - Your production domain URLs.

---

## 🚀 Running Locally

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure .env with your Supabase and Gemini credentials
cp .env.example .env

# 3. Start the FastAPI + Uvicorn server
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```
Open [http://localhost:8000](http://localhost:8000) in your browser.

---

## 🎯 Study Modes

1. **Simplify with Syllabus** (`simplify` with notes + syllabus):
   - Generates a full module-by-module coverage map (`Covered` / `Partly covered` / `Missing from notes`).
   - Explains core concepts in syllabus sequence with everyday analogies and worked examples.
   - Highlights gaps in notes and fills them with `➕ Added` explanations.
   - Generates 10 terse revision bullets and self-check questions per module.

2. **Simplify Notes Only** (`simplify` with notes only):
   - Distills raw lecture notes without assuming unverified syllabus boundaries.
   - Outlines the "Big Picture", section-by-section plain-language guides, Key Terms glossary, and self-checks.
   - Flags doubtful or contradictory points with `✏️ Correction` tags.

3. **Predict the Paper** (`predict` with previous year papers + notes/syllabus):
   - Inventories question patterns across examination series (KTU 2015, 2019, 2024 schemes).
   - Computes weighted topic recurrence probabilities (`🔴 Very likely`, `🟠 Likely`, `🟡 Possible`).
   - Drafts a complete mock examination paper (Part A + Part B module pairs) with step-by-step answer hints.

---

## 📡 API Specification

| Endpoint | Method | Auth Required | Description |
|---|---|---|---|
| `/api/config` | `GET` | No | Returns public `{ supabaseUrl, supabaseAnonKey }` for frontend SDK initialization |
| `/api/auth/me` | `GET` | Yes (Supabase Bearer Token) | Retrieves user profile and daily quota usage `{ id, name, email, usage: { used, limit } }` |
| `/api/process` | `POST` | Yes (Supabase Bearer Token) | Multipart handler for study materials; returns `{ id, title, output, usage }` |
| `/api/history` | `GET` | Yes (Supabase Bearer Token) | Lists all saved study sessions for current user |
| `/api/history/{id}` | `GET` | Yes (Supabase Bearer Token) | Fetches single study session detail |
| `/api/history/{id}` | `DELETE` | Yes (Supabase Bearer Token) | Deletes study session record |

---

## 🛡️ Production & Security Invariants

- **Row Level Security (RLS)**: PostgreSQL enforces that users cannot query or mutate records where `auth.uid() != user_id`.
- **Zero Secret Leakage**: The `SUPABASE_SERVICE_KEY` is restricted strictly to backend server processes and never exposed to client browsers.
- **Client SDK Auth**: Clients authenticate directly via Google OAuth using `@supabase/supabase-js`, passing the secure JWT token as `Authorization: Bearer <access_token>`.
