import hashlib
import os
import re

from shared.ai_classifier import classify_intent_and_sentiment
from shared.core_db import (
    EVENT_STATUS_BLACKLISTED,
    EVENT_STATUS_PENDING_REVIEW,
    EVENT_STATUS_PROCESSED,
    EVENT_STATUS_RATE_LIMITED,
    EVENT_STATUS_SPAM,
    add_user_to_blacklist,
    count_recent_user_events,
    create_inbound_event,
    is_user_blacklisted,
    record_message_fingerprint,
    update_event_status,
)
from shared.message_schema import utc_now_iso


def normalize_message(message):
    text = (message or "").lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text


def hash_message(message):
    normalized = normalize_message(message)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:32]


def contains_link(message):
    text = (message or "").lower()
    return "http://" in text or "https://" in text or "www." in text


def is_repeated_spam(conn, user_id, page_id, message):
    threshold = int(os.getenv("SPAM_REPEAT_THRESHOLD", "3"))
    repeat_count = record_message_fingerprint(conn, user_id, page_id, hash_message(message))
    return repeat_count >= threshold


def is_rate_limited(conn, user_id, page_id):
    window_seconds = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
    max_messages = int(os.getenv("RATE_LIMIT_MAX_MESSAGES", "5"))
    recent_count = count_recent_user_events(conn, user_id, page_id, window_seconds)
    return recent_count > max_messages


def should_escalate_to_admin(intent, sentiment, message):
    text = normalize_message(message)
    if intent in {"complaint", "escalate_admin"}:
        return True
    if sentiment == "negative" and any(word in text for word in ("hoan tien", "refund", "lua dao", "scam")):
        return True
    return False


def decide_action(intent, sentiment, *, channel, is_spam, escalate_admin):
    if is_spam:
        if channel == "comment":
            return "hide", "Binh luan spam da duoc an va user da vao blacklist."
        return "escalate_admin", "Tin nhan spam da chuyen admin xu ly."

    if escalate_admin:
        if sentiment == "negative":
            return "escalate_admin", "Da chuyen admin ho tro. Rat xin loi vi trai nghiem chua tot."
        if intent == "ask_price":
            return "escalate_admin", "Da chuyen admin tu van gia. Shop se phan hoi ban som."
        return "escalate_admin", "Da chuyen admin xu ly yeu cau cua ban."

    if sentiment == "negative":
        return "reply", "Rat xin loi vi trai nghiem chua tot, ben minh se kiem tra ngay."
    if sentiment == "positive" or intent == "praise":
        return "reply", "Cam on ban da ung ho page!"
    if intent == "ask_price":
        return "reply", "Cam on ban da quan tam. Shop se gui bang gia som nhat."
    return "reply", "Cam on ban, shop se phan hoi ban som."


def build_reply_command(event, action, reply_text, intent, sentiment):
    return {
        "schema_version": 1,
        "command_id": f"cmd_{event.get('event_id', 'unknown')}",
        "event_id": event.get("event_id", "unknown"),
        "action": action,
        "target": {
            "page_id": event.get("page_id"),
            "comment_id": event.get("comment_id"),
            "user_id": event.get("user_id"),
            "message_id": event.get("message_id"),
            "channel": event.get("channel"),
        },
        "payload": {
            "reply_text": reply_text,
            "message": reply_text,
        },
        "intent": intent,
        "sentiment": sentiment,
        "created_at": utc_now_iso(),
        "retry_count": 0,
    }


def process_raw_event(conn, event):
    user_id = event.get("user_id", "")
    page_id = event.get("page_id", "")
    message = event.get("message", "")
    channel = event.get("channel", "comment")
    event_id = event.get("event_id", "unknown")

    created_state, existing_status = create_inbound_event(conn, event)
    if created_state == "duplicate":
        return None, existing_status

    if is_user_blacklisted(conn, user_id, page_id):
        update_event_status(conn, event_id, EVENT_STATUS_BLACKLISTED)
        return None, EVENT_STATUS_BLACKLISTED

    if is_rate_limited(conn, user_id, page_id):
        update_event_status(
            conn,
            event_id,
            EVENT_STATUS_RATE_LIMITED,
            intent="rate_limit",
            sentiment="neutral",
            action="escalate_admin",
        )
        command = build_reply_command(
            event,
            "escalate_admin",
            "Ban dang gui qua nhieu tin nhan. Da chuyen admin ho tro.",
            "rate_limit",
            "neutral",
        )
        update_event_status(
            conn,
            event_id,
            EVENT_STATUS_PENDING_REVIEW,
            intent="rate_limit",
            sentiment="neutral",
            action="escalate_admin",
            command_id=command["command_id"],
        )
        return command, EVENT_STATUS_PENDING_REVIEW

    link_spam = contains_link(message)
    repeat_spam = is_repeated_spam(conn, user_id, page_id, message)
    is_spam = link_spam or repeat_spam

    intent, sentiment = classify_intent_and_sentiment(message)
    if is_spam:
        intent = "spam"
        sentiment = "negative"

    escalate_admin = should_escalate_to_admin(intent, sentiment, message)
    action, reply_text = decide_action(
        intent,
        sentiment,
        channel=channel,
        is_spam=is_spam,
        escalate_admin=escalate_admin,
    )

    if is_spam:
        add_user_to_blacklist(
            conn,
            user_id,
            page_id,
            "link_spam" if link_spam else "repeat_spam",
        )

    command = build_reply_command(event, action, reply_text, intent, sentiment)
    final_status = EVENT_STATUS_SPAM if is_spam else EVENT_STATUS_PROCESSED
    if action == "escalate_admin":
        final_status = EVENT_STATUS_PENDING_REVIEW

    update_event_status(
        conn,
        event_id,
        final_status,
        intent=intent,
        sentiment=sentiment,
        action=action,
        command_id=command["command_id"],
    )
    return command, final_status
