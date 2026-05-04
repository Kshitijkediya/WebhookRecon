import hashlib
import hmac
import json

import pytest
from httpx import AsyncClient

WEBHOOK_SECRET = "test_secret"


def sign_payload(payload: dict, secret: str = WEBHOOK_SECRET) -> str:
    body = json.dumps(payload).encode()
    sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={sig}"


@pytest.mark.asyncio
async def test_receive_webhook_accepted(client: AsyncClient, monkeypatch):
    monkeypatch.setenv("WEBHOOK_SECRET", WEBHOOK_SECRET)
    payload = {"id": "evt_001", "type": "payment.succeeded"}
    headers = {"x-webhook-signature": sign_payload(payload)}

    response = await client.post(
        "/webhooks/receive?provider=stripe",
        json=payload,
        headers=headers,
    )
    assert response.status_code == 202
    assert response.json()["status"] == "accepted"


@pytest.mark.asyncio
async def test_receive_webhook_invalid_signature(client: AsyncClient):
    payload = {"id": "evt_002", "type": "payment.succeeded"}
    headers = {"x-webhook-signature": "sha256=invalidsig"}

    response = await client.post(
        "/webhooks/receive?provider=stripe",
        json=payload,
        headers=headers,
    )
    assert response.status_code == 401
