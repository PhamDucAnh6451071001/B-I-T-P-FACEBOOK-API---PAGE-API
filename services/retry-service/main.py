import logging
import os
import sys
import threading
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from shared.kafka_utils import create_consumer, create_producer  # noqa: E402
from shared.retry_handler import process_failed_message  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("retry-service")

MAX_RETRY = int(os.getenv("MAX_RETRY", "3"))
METRICS = {
    "messages_processed": 0,
    "retries_published": 0,
    "dlq_published": 0,
    "errors": 0,
}

app = FastAPI(title="retry-service")


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "retry-service",
        "max_retry": MAX_RETRY,
        "metrics": METRICS,
    }


@app.get("/metrics")
async def metrics():
    lines = [
        "# HELP retry_service_messages_processed Total send_failed messages handled",
        "# TYPE retry_service_messages_processed counter",
        f"retry_service_messages_processed {METRICS['messages_processed']}",
        "# HELP retry_service_retries_published Total messages republished to send_retry",
        "# TYPE retry_service_retries_published counter",
        f"retry_service_retries_published {METRICS['retries_published']}",
        "# HELP retry_service_dlq_published Total messages moved to dead_letter",
        "# TYPE retry_service_dlq_published counter",
        f"retry_service_dlq_published {METRICS['dlq_published']}",
        "# HELP retry_service_errors Total retry worker errors",
        "# TYPE retry_service_errors counter",
        f"retry_service_errors {METRICS['errors']}",
        "# HELP retry_service_max_retry Configured max retry attempts",
        "# TYPE retry_service_max_retry gauge",
        f"retry_service_max_retry {MAX_RETRY}",
    ]
    return PlainTextResponse("\n".join(lines) + "\n", media_type="text/plain; version=0.0.4")


def run_consumer():
    consumer = create_consumer(["send_failed"], group_id=os.getenv("RETRY_GROUP_ID", "retry-service-group"))
    producer = create_producer()

    for msg in consumer:
        failed = msg.value
        try:
            def publish_retry(retry_msg):
                producer.send("send_retry", retry_msg)
                METRICS["retries_published"] += 1

            def publish_dlq(dlq_msg):
                producer.send("dead_letter", dlq_msg)
                METRICS["dlq_published"] += 1

            outcome = process_failed_message(
                failed,
                max_retry=MAX_RETRY,
                publish_retry=publish_retry,
                publish_dlq=publish_dlq,
            )
            producer.flush()
            METRICS["messages_processed"] += 1
            if outcome["result"] == "retry":
                logger.info(
                    "Republished command=%s to send_retry count=%s backoff=%ss",
                    failed.get("command_id"),
                    outcome["retry_count"],
                    outcome["backoff_seconds"],
                )
            else:
                logger.error(
                    "Moved command=%s to dead_letter after %s attempts",
                    failed.get("command_id"),
                    outcome["retry_count"],
                )
        except Exception:
            METRICS["errors"] += 1
            logger.exception("Failed processing send_failed command=%s", failed.get("command_id"))


def start_consumer_thread():
    thread = threading.Thread(target=run_consumer, daemon=True, name="retry-consumer")
    thread.start()
    return thread


@app.on_event("startup")
async def startup_event():
    start_consumer_thread()
    logger.info("Retry consumer started with MAX_RETRY=%s", MAX_RETRY)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "3003")))
