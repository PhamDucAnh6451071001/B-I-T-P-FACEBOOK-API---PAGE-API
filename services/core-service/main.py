import logging
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from shared.core_db import db_connection  # noqa: E402
from shared.core_processing import process_raw_event  # noqa: E402
from shared.kafka_utils import create_consumer, create_producer  # noqa: E402
from shared.message_schema import validate_raw_event  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("core-service")


def run():
    consumer = create_consumer(["raw_events"], group_id=os.getenv("CORE_GROUP_ID", "core-service-group"))
    producer = create_producer()
    for msg in consumer:
        event = msg.value
        validate_raw_event(event)
        with db_connection() as conn:
            command, status = process_raw_event(conn, event)

        if command is None:
            logger.info("Skip event_id=%s status=%s", event.get("event_id"), status)
            continue

        producer.send("reply_commands", command)
        producer.flush()
        logger.info(
            "Published reply command=%s action=%s status=%s",
            command["command_id"],
            command["action"],
            status,
        )


if __name__ == "__main__":
    run()
