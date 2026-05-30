import json
import os
from kafka import KafkaConsumer, KafkaProducer


def get_bootstrap_servers():
    return os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092").split(",")


def create_producer():
    return KafkaProducer(
        bootstrap_servers=get_bootstrap_servers(),
        value_serializer=lambda value: json.dumps(value).encode("utf-8"),
    )


def create_consumer(topics, group_id):
    return KafkaConsumer(
        *topics,
        bootstrap_servers=get_bootstrap_servers(),
        group_id=group_id,
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        value_deserializer=lambda value: json.loads(value.decode("utf-8")),
    )
