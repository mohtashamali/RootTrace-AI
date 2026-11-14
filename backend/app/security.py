import hashlib
import hmac

from fastapi import Header, HTTPException

from app.config import get_settings


def require_admin(authorization: str = Header(default="")) -> None:
    """Protects dashboard endpoints. Disabled only when ADMIN_ACCESS_KEY is empty (local dev)."""
    key = get_settings().admin_access_key
    if not key:
        return
    token = authorization.removeprefix("Bearer ").strip()
    if not hmac.compare_digest(token.encode(), key.encode()):
        raise HTTPException(401, "Missing or invalid access key.")


def verify_github_signature(body: bytes, signature: str, secret: str) -> bool:
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature or "")
