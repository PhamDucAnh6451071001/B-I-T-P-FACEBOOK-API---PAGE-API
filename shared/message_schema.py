from datetime import datetime, timezone


def utc_now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def validate_reply_command(data):
    required_fields = ["schema_version", "command_id", "event_id", "action", "payload", "created_at"]
    missing = [field for field in required_fields if field not in data]
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")

    if data["action"] not in {"reply", "hide", "post", "escalate_admin"}:
        raise ValueError("action must be one of: reply, hide, post, escalate_admin")

    return data


def validate_raw_event(data):
    required_fields = ["schema_version", "event_id", "event_type", "page_id", "channel", "created_at"]
    missing = [field for field in required_fields if field not in data]
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")
    if data["event_type"] not in {"comment_created", "message_created"}:
        raise ValueError("event_type must be comment_created or message_created")
    if data["channel"] not in {"comment", "messenger"}:
        raise ValueError("channel must be comment or messenger")
    return data


def validate_failed_or_retry_message(data):
    required_fields = ["schema_version", "command_id", "event_id", "retry_count", "payload"]
    missing = [field for field in required_fields if field not in data]
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")
    return data


def build_failed_message(command, error_message):
    retry_count = int(command.get("retry_count", 0))
    return {
        "schema_version": 1,
        "command_id": command.get("command_id", "unknown"),
        "event_id": command.get("event_id", "unknown"),
        "retry_count": retry_count,
        "last_error": error_message,
        "failed_at": utc_now_iso(),
        "payload": command.get("payload", {}),
        "action": command.get("action"),
        "target": command.get("target", {}),
        "created_at": utc_now_iso(),
    }
