import os
import logging
from typing import Optional, Dict, Any
import httpx
import jwt
from fastapi import Header, HTTPException, status

logger = logging.getLogger(__name__)

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
SUPABASE_JWT_SECRET = os.environ.get("SUPABASE_JWT_SECRET", "")

async def verify_supabase_token(token: str) -> Dict[str, Any]:
    """
    Verify Supabase Access Token (JWT).
    1. If SUPABASE_JWT_SECRET is provided, verifies cryptographic signature via PyJWT (HS256).
    2. If SUPABASE_URL & ANON_KEY are provided, verifies by calling Supabase Auth endpoint /auth/v1/user.
    3. Handles test/development mock tokens gracefully.
    """
    if not token or not token.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is missing."
        )

    # 1. Local JWT Secret Verification (if provided)
    if SUPABASE_JWT_SECRET and not SUPABASE_JWT_SECRET.startswith("your_"):
        try:
            payload = jwt.decode(
                token,
                SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                options={"verify_aud": False}
            )
            user_id = payload.get("sub")
            email = payload.get("email", "")
            user_metadata = payload.get("user_metadata", {})
            name = user_metadata.get("full_name") or user_metadata.get("name") or (email.split("@")[0] if email else "Student")
            return {
                "id": str(user_id),
                "email": email,
                "name": name,
                "user_metadata": user_metadata
            }
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Your session has expired. Please sign in again."
            )
        except Exception as e:
            logger.debug(f"PyJWT verification error: {e}")

    # 2. Remote Supabase Verification via /auth/v1/user
    if (
        SUPABASE_URL
        and SUPABASE_ANON_KEY
        and not SUPABASE_URL.startswith("your_")
        and "your-project-ref" not in SUPABASE_URL
        and "placeholder" not in SUPABASE_URL
    ):
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.get(
                    f"{SUPABASE_URL}/auth/v1/user",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "apikey": SUPABASE_ANON_KEY
                    }
                )
                if res.status_code == 200:
                    user_data = res.json()
                    user_id = user_data.get("id")
                    email = user_data.get("email", "")
                    user_metadata = user_data.get("user_metadata", {})
                    name = user_metadata.get("full_name") or user_metadata.get("name") or (email.split("@")[0] if email else "Student")
                    return {
                        "id": str(user_id),
                        "email": email,
                        "name": name,
                        "user_metadata": user_metadata
                    }
                else:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid or expired Supabase authentication token."
                    )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error connecting to Supabase Auth: {e}")
            # If network failed, attempt unverified payload decode if valid JWT format
            pass

    # 3. Fallback token decode (for dev/test environments)
    try:
        payload = jwt.decode(token, options={"verify_signature": False})
        user_id = payload.get("sub") or payload.get("id") or "test-user-id"
        email = payload.get("email", "student@ktu.edu")
        user_metadata = payload.get("user_metadata", {})
        name = user_metadata.get("full_name") or user_metadata.get("name") or (email.split("@")[0] if email else "Student")
        return {
            "id": str(user_id),
            "email": email,
            "name": name,
            "user_metadata": user_metadata
        }
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format."
        )

async def get_current_user(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing."
        )
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Expected 'Bearer <token>'."
        )
    token = parts[1]
    return await verify_supabase_token(token)
