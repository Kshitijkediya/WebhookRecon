import hashlib
import hmac

from fastapi import Header, HTTPException, Request

from app.core.config import settings


async def verify_signature(
    request: Request,
    x_webhook_signature: str = Header(...),
) -> None:
    body = await request.body()
    expected = hmac.new(
        settings.webhook_secret.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(f"sha256={expected}", x_webhook_signature):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
