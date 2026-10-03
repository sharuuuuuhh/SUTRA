import os
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import httpx

logger = logging.getLogger(__name__)

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")

# In-memory storage fallback for local testing when Supabase credentials are not yet entered
_mem_history: List[dict] = []
_mem_usage: List[dict] = []
_mem_id_counter = 1

def is_supabase_configured() -> bool:
    return bool(
        SUPABASE_URL
        and SUPABASE_SERVICE_KEY
        and not SUPABASE_URL.startswith("your_")
        and "your-project-ref" not in SUPABASE_URL
        and "placeholder" not in SUPABASE_URL
    )

def get_supabase_client():
    if not is_supabase_configured():
        return None
    try:
        from supabase import create_client, Client
        return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    except Exception as e:
        logger.warning(f"Error creating Supabase client: {e}")
        return None

def get_today_usage(user_id: str) -> int:
    today_start = datetime.now(timezone.utc).strftime("%Y-%m-%dT00:00:00Z")
    client = get_supabase_client()
    
    if client:
        try:
            res = client.table("usage_logs") \
                .select("id", count="exact") \
                .eq("user_id", str(user_id)) \
                .gte("created_at", today_start) \
                .execute()
            return res.count or 0
        except Exception as e:
            logger.error(f"Error fetching usage from Supabase: {e}")
    
    # Fallback in-memory
    count = 0
    today_prefix = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for log in _mem_usage:
        if str(log["user_id"]) == str(user_id) and log["created_at"].startswith(today_prefix):
            count += 1
    return count

def record_usage(user_id: str):
    now_iso = datetime.now(timezone.utc).isoformat()
    client = get_supabase_client()
    
    if client:
        try:
            client.table("usage_logs").insert({
                "user_id": str(user_id),
                "created_at": now_iso
            }).execute()
            return
        except Exception as e:
            logger.error(f"Error recording usage in Supabase: {e}")

    # Fallback in-memory
    _mem_usage.append({
        "user_id": str(user_id),
        "created_at": now_iso
    })

def save_history(
    user_id: str,
    mode: str,
    subject: str,
    depth: str,
    language: str,
    scheme: str,
    title: str,
    output: str
) -> dict:
    global _mem_id_counter
    now_iso = datetime.now(timezone.utc).isoformat()
    client = get_supabase_client()
    
    payload = {
        "user_id": str(user_id),
        "mode": mode,
        "subject": subject,
        "depth": depth,
        "language": language,
        "scheme": scheme,
        "title": title,
        "output": output,
        "created_at": now_iso
    }

    if client:
        try:
            res = client.table("history").insert(payload).execute()
            if res.data and len(res.data) > 0:
                return res.data[0]
        except Exception as e:
            logger.error(f"Error inserting history into Supabase: {e}")

    # Fallback in-memory
    record = dict(payload)
    record["id"] = _mem_id_counter
    _mem_id_counter += 1
    _mem_history.append(record)
    return record

def list_history(user_id: str) -> List[dict]:
    client = get_supabase_client()
    
    if client:
        try:
            res = client.table("history") \
                .select("id, mode, subject, depth, language, scheme, title, created_at") \
                .eq("user_id", str(user_id)) \
                .order("id", desc=True) \
                .execute()
            return res.data or []
        except Exception as e:
            logger.error(f"Error listing history from Supabase: {e}")

    # Fallback in-memory (strictly filtered by user_id)
    results = []
    for item in reversed(_mem_history):
        if str(item["user_id"]) == str(user_id):
            results.append({
                "id": item["id"],
                "mode": item["mode"],
                "subject": item["subject"],
                "depth": item["depth"],
                "language": item["language"],
                "scheme": item["scheme"],
                "title": item["title"],
                "created_at": item["created_at"]
            })
    return results

def get_history_item(user_id: str, item_id: int) -> Optional[dict]:
    client = get_supabase_client()
    
    if client:
        try:
            res = client.table("history") \
                .select("*") \
                .eq("id", item_id) \
                .eq("user_id", str(user_id)) \
                .execute()
            if res.data and len(res.data) > 0:
                return res.data[0]
            return None
        except Exception as e:
            logger.error(f"Error getting history item from Supabase: {e}")

    # Fallback in-memory (strictly filtered by user_id and item_id)
    for item in _mem_history:
        if str(item["id"]) == str(item_id) and str(item["user_id"]) == str(user_id):
            return item
    return None

def delete_history_item(user_id: str, item_id: int) -> bool:
    global _mem_history
    client = get_supabase_client()
    
    if client:
        try:
            res = client.table("history") \
                .delete() \
                .eq("id", item_id) \
                .eq("user_id", str(user_id)) \
                .execute()
            return bool(res.data and len(res.data) > 0)
        except Exception as e:
            logger.error(f"Error deleting history item from Supabase: {e}")

    # Fallback in-memory
    before_count = len(_mem_history)
    _mem_history = [
        item for item in _mem_history
        if not (str(item["id"]) == str(item_id) and str(item["user_id"]) == str(user_id))
    ]
    return len(_mem_history) < before_count
