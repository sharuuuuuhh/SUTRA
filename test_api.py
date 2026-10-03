import os
import sys
import uuid
import jwt
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)

def make_test_supabase_token(user_id: str, email: str, name: str) -> str:
    payload = {
        "sub": str(user_id),
        "email": email,
        "user_metadata": {
            "full_name": name,
            "name": name
        },
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "exp": int((datetime.now(timezone.utc) + timedelta(days=7)).timestamp())
    }
    # Unsigned / mock token decode supported by fallback
    return jwt.encode(payload, "test_secret_for_mocking", algorithm="HS256")

def run_tests():
    print("--- 1. Testing /api/config ---")
    r_cfg = client.get("/api/config")
    assert r_cfg.status_code == 200
    cfg = r_cfg.json()
    assert "supabaseUrl" in cfg and "supabaseAnonKey" in cfg
    print("[PASS] /api/config verified.")

    print("--- 2. Testing Supabase Token Auth & /api/auth/me ---")
    user_a_id = str(uuid.uuid4())
    token_a = make_test_supabase_token(user_a_id, "alice@ktu.edu", "Alice Menon")
    headers_a = {"Authorization": f"Bearer {token_a}"}

    r_me = client.get("/api/auth/me", headers=headers_a)
    assert r_me.status_code == 200, f"Expected 200, got {r_me.status_code}: {r_me.text}"
    data_a = r_me.json()
    assert data_a["id"] == user_a_id
    assert data_a["name"] == "Alice Menon"
    assert data_a["email"] == "alice@ktu.edu"
    assert data_a["usage"]["used"] == 0
    assert data_a["usage"]["limit"] == 10
    print("[PASS] Supabase token auth and /api/auth/me verified.")

    print("--- 3. Testing Missing and Invalid Auth Tokens ---")
    # No auth header
    r_no_auth = client.get("/api/auth/me")
    assert r_no_auth.status_code == 401

    # Malformed auth header
    r_bad_auth = client.get("/api/auth/me", headers={"Authorization": "Basic 12345"})
    assert r_bad_auth.status_code == 401
    print("[PASS] Unauthorized checks passed.")

    print("--- 4. Testing File Validations on /api/process ---")
    # Simplify without notes
    r_err = client.post("/api/process", data={"mode": "simplify", "subject": "CS201"}, headers=headers_a)
    assert r_err.status_code == 400

    # Unsupported file type (e.g. .exe)
    files = {"notes": ("malicious.exe", b"executable bytes", "application/octet-stream")}
    r_unsup = client.post("/api/process", data={"mode": "simplify", "subject": "CS201"}, files=files, headers=headers_a)
    assert r_unsup.status_code == 415

    # Predict without past papers
    files_n = {"notes": ("notes.txt", b"Deadlock notes...", "text/plain")}
    r_pred_err = client.post("/api/process", data={"mode": "predict", "subject": "CS201"}, files=files_n, headers=headers_a)
    assert r_pred_err.status_code == 400
    print("[PASS] File validation rules passed.")

    print("--- 5. Testing Multi-User Scoped History Isolation (RLS) ---")
    user_b_id = str(uuid.uuid4())
    token_b = make_test_supabase_token(user_b_id, "bob@ktu.edu", "Bob Thomas")
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Save a history item for Alice
    from backend.db import save_history
    hist_item = save_history(
        user_id=user_a_id,
        mode="simplify",
        subject="CST301 OS",
        depth="standard",
        language="english",
        scheme="2019",
        title="CST301 OS - Simplify",
        output="## Module 3 Deadlocks Guide\n\nContent here."
    )
    hist_id = hist_item["id"]

    # Alice should see her record in history list
    r_hist_a = client.get("/api/history", headers=headers_a)
    assert r_hist_a.status_code == 200
    assert any(item["id"] == hist_id for item in r_hist_a.json())

    # Alice can fetch her record detail
    r_item_a = client.get(f"/api/history/{hist_id}", headers=headers_a)
    assert r_item_a.status_code == 200
    assert r_item_a.json()["title"] == "CST301 OS - Simplify"

    # Bob CANNOT see Alice's record in his history list
    r_hist_b = client.get("/api/history", headers=headers_b)
    assert r_hist_b.status_code == 200
    assert not any(item["id"] == hist_id for item in r_hist_b.json())

    # Bob attempting to GET Alice's record directly MUST return 404
    r_get_b = client.get(f"/api/history/{hist_id}", headers=headers_b)
    assert r_get_b.status_code == 404

    # Bob attempting to DELETE Alice's record MUST return 404
    r_del_b = client.delete(f"/api/history/{hist_id}", headers=headers_b)
    assert r_del_b.status_code == 404

    # Alice deleting her record succeeds
    r_del_a = client.delete(f"/api/history/{hist_id}", headers=headers_a)
    assert r_del_a.status_code == 200
    r_hist_a2 = client.get("/api/history", headers=headers_a)
    assert not any(item["id"] == hist_id for item in r_hist_a2.json())
    print("[PASS] User isolation (RLS) & history CRUD operations passed.")

    print("\nSUCCESS: ALL SUPABASE AUTH & RLS TESTS PASSED PERFECTLY!")

if __name__ == "__main__":
    run_tests()
