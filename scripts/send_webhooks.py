"""Send signed test webhooks to a running WebhookRecon API.

Run from the project root:
    .venv/Scripts/python.exe scripts/send_webhooks.py --count 5
"""

import argparse
import hashlib
import hmac
import json
import time
import uuid

import httpx

from app.core.config import settings


def sign(body: bytes, secret: str) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Send signed test webhooks.")
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--provider", default="razorpay")
    parser.add_argument("--count", type=int, default=5)
    parser.add_argument(
        "--delay", type=float, default=1.0, help="seconds between webhooks"
    )
    args = parser.parse_args()

    for i in range(1, args.count + 1):
        payload = {
            "id": f"evt_{uuid.uuid4().hex[:12]}",
            "type": "payment.succeeded",
            "transaction_id": f"pay_{uuid.uuid4().hex[:12]}",
            "amount": 49900,
            "currency": "INR",
        }
        # Sign the exact bytes we send: the signature covers raw bytes, not the dict.
        body = json.dumps(payload).encode()
        response = httpx.post(
            f"{args.url}/webhooks/receive",
            params={"provider": args.provider},
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Webhook-Signature": sign(body, settings.webhook_secret),
            },
        )
        print(f"{i}. {payload['id']} -> {response.status_code} {response.json()}")
        time.sleep(args.delay)


if __name__ == "__main__":
    main()
