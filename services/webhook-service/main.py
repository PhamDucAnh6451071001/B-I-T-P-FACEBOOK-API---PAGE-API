import hashlib
import hmac
import logging
import os
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from shared.kafka_utils import create_producer  # noqa: E402
from shared.webhook_normalize import normalize_webhook_payload  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("webhook-service")

app = FastAPI(title="webhook-service")
producer = create_producer()
VERIFY_TOKEN = os.getenv("FB_WEBHOOK_VERIFY_TOKEN", "verify-token")
APP_SECRET = os.getenv("FB_APP_SECRET", "")


def verify_signature(body: bytes, signature: str) -> bool:
    if not APP_SECRET or not signature:
        return False
    expected = "sha256=" + hmac.new(APP_SECRET.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


@app.get("/webhook")
async def verify_webhook(request: Request):
    mode = request.query_params.get("hub.mode")
    challenge = request.query_params.get("hub.challenge")
    token = request.query_params.get("hub.verify_token")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return PlainTextResponse(content=challenge or "", status_code=200)
    raise HTTPException(status_code=403, detail="Webhook verification failed")


@app.post("/webhook")
async def receive_webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("x-hub-signature-256", "")
    if not verify_signature(body, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    payload = await request.json()
    events = normalize_webhook_payload(payload)
    for event in events:
        producer.send("raw_events", event)
        logger.info(
            "Published raw_events event_id=%s type=%s channel=%s",
            event["event_id"],
            event["event_type"],
            event["channel"],
        )
    producer.flush()
    return {"status": "ok", "published": len(events)}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "webhook-service"}
