import json
import logging
from django.conf import settings
from django.core.management.base import BaseCommand
from kafka import KafkaConsumer, KafkaProducer
from pageapi.kafka_processing import process_command


class Command(BaseCommand):
    help = "Consume reply_commands and send_retry topics, call Facebook, publish send_failed on error."

    def handle(self, *args, **options):
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
        bootstrap_servers = settings.KAFKA_BOOTSTRAP_SERVERS.split(",")

        consumer = KafkaConsumer(
            "reply_commands",
            "send_retry",
            bootstrap_servers=bootstrap_servers,
            group_id=settings.KAFKA_GROUP_ID,
            auto_offset_reset="earliest",
            enable_auto_commit=True,
            value_deserializer=lambda value: json.loads(value.decode("utf-8")),
        )
        producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda value: json.dumps(value).encode("utf-8"),
        )

        logger = logging.getLogger("backend_api.consumer")
        logger.info("Kafka consumer started on topics: reply_commands, send_retry")

        def publish_failed(message):
            producer.send("send_failed", message)
            producer.flush()

        for msg in consumer:
            result = process_command(msg.value, msg.topic, publish_failed)
            logger.info("Processed offset=%s topic=%s result=%s", msg.offset, msg.topic, result["status"])
