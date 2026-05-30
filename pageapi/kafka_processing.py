import logging
from django.db import IntegrityError, transaction
from pageapi.facebook_client import send_action_to_facebook
from pageapi.models import CommentHistory, IdempotencyKey
from shared.message_schema import build_failed_message, validate_reply_command

logger = logging.getLogger("backend_api.kafka")


def is_processed(command_id):
    return IdempotencyKey.objects.filter(command_id=command_id).exists()


def mark_processed(command_id, event_id, source_topic):
    try:
        with transaction.atomic():
            IdempotencyKey.objects.create(
                command_id=command_id,
                event_id=event_id,
                source_topic=source_topic,
                status="processed",
            )
            return True
    except IntegrityError:
        return False


def record_comment_history(command, source_topic, fb_result, status="processed"):
    target = command.get("target", {})
    payload = command.get("payload", {})
    CommentHistory.objects.create(
        command_id=command.get("command_id", ""),
        event_id=command.get("event_id", ""),
        page_id=target.get("page_id", ""),
        user_id=target.get("user_id", ""),
        comment_id=target.get("comment_id"),
        message_id=target.get("message_id"),
        channel=target.get("channel", "comment"),
        action=command.get("action", ""),
        user_message=payload.get("message", ""),
        reply_text=payload.get("reply_text", ""),
        status=status,
        source_topic=source_topic,
        facebook_response=fb_result if isinstance(fb_result, dict) else {"result": fb_result},
    )


def process_command(command, source_topic, publish_failed):
    command = validate_reply_command(command)
    command_id = command["command_id"]
    event_id = command["event_id"]

    if is_processed(command_id):
        logger.info("Skip duplicate command_id=%s from topic=%s", command_id, source_topic)
        return {"status": "skipped_duplicate", "command_id": command_id}

    try:
        fb_result = send_action_to_facebook(command)
        mark_processed(command_id, event_id, source_topic)
        record_comment_history(command, source_topic, fb_result, status="processed")
        logger.info("Processed command_id=%s topic=%s", command_id, source_topic)
        return {"status": "processed", "command_id": command_id, "facebook_result": fb_result}
    except Exception as exc:
        failed_message = build_failed_message(command, str(exc))
        publish_failed(failed_message)
        record_comment_history(command, source_topic, {"error": str(exc)}, status="failed")
        logger.exception("Failed command_id=%s topic=%s", command_id, source_topic)
        return {"status": "failed", "command_id": command_id, "error": str(exc)}
