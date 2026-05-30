#!/usr/bin/env bash
set -euo pipefail

TOPICS=("raw_events" "reply_commands" "send_failed" "send_retry" "dead_letter")

for topic in "${TOPICS[@]}"; do
  docker exec -it fb_api-kafka kafka-topics \
    --create \
    --if-not-exists \
    --topic "$topic" \
    --bootstrap-server localhost:9092 \
    --partitions 1 \
    --replication-factor 1
done

echo "Kafka topics ready."
