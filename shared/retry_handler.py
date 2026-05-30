import time

from shared.message_schema import utc_now_iso, validate_failed_or_retry_message


def compute_backoff_seconds(retry_count):
    return 1 * (2 ** (retry_count - 1))


def build_retry_message(failed, retry_count):
    return {
        **failed,
        "retry_count": retry_count,
        "next_retry_at": utc_now_iso(),
    }


def build_dlq_message(failed, retry_count):
    return {
        "schema_version": 1,
        "command_id": failed.get("command_id"),
        "event_id": failed.get("event_id"),
        "retry_count": retry_count,
        "failed_at": utc_now_iso(),
        "final_error": failed.get("last_error", "unknown"),
        "original_topic": "send_failed",
        "payload": failed.get("payload", {}),
        "target": failed.get("target", {}),
        "action": failed.get("action"),
    }


def process_failed_message(
    failed,
    *,
    max_retry,
    publish_retry,
    publish_dlq,
    sleep_fn=time.sleep,
):
    validate_failed_or_retry_message(failed)
    retry_count = int(failed.get("retry_count", 0)) + 1
    backoff_seconds = compute_backoff_seconds(retry_count)
    sleep_fn(backoff_seconds)

    if retry_count <= max_retry:
        retry_msg = build_retry_message(failed, retry_count)
        publish_retry(retry_msg)
        return {"result": "retry", "retry_count": retry_count, "backoff_seconds": backoff_seconds}

    dlq_msg = build_dlq_message(failed, retry_count)
    publish_dlq(dlq_msg)
    return {"result": "dlq", "retry_count": retry_count, "backoff_seconds": backoff_seconds}
