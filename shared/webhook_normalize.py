from shared.message_schema import utc_now_iso


def build_raw_event(
    *,
    event_id,
    event_type,
    page_id,
    message,
    user_id="",
    post_id=None,
    comment_id=None,
    message_id=None,
    channel="comment",
    raw_payload=None,
):
    return {
        "schema_version": 1,
        "event_id": event_id,
        "event_type": event_type,
        "source": "facebook",
        "channel": channel,
        "page_id": str(page_id) if page_id else "",
        "post_id": post_id,
        "comment_id": comment_id,
        "message_id": message_id,
        "user_id": str(user_id) if user_id else "",
        "message": message or "",
        "created_at": utc_now_iso(),
        "raw_payload": raw_payload or {},
    }


def normalize_feed_change(page_id, change):
    field = change.get("field", "feed")
    value = change.get("value", {})
    if field not in {"feed", "comments"}:
        return None

    verb = value.get("verb", "add")
    created_time = value.get("created_time", "0")
    comment_id = value.get("comment_id")
    post_id = value.get("post_id")
    if not comment_id and verb != "add":
        return None

    event_id = f"comment_{page_id}_{comment_id or 'unknown'}_{verb}_{created_time}"
    return build_raw_event(
        event_id=event_id,
        event_type="comment_created",
        page_id=page_id,
        message=value.get("message") or "",
        user_id=value.get("from", {}).get("id", ""),
        post_id=post_id,
        comment_id=comment_id,
        channel="comment",
        raw_payload={"field": field, **value},
    )


def normalize_messaging_event(page_id, messaging_event):
    message = messaging_event.get("message") or {}
    text = message.get("text") or ""
    mid = message.get("mid")
    if not mid and not text:
        return None

    sender_id = messaging_event.get("sender", {}).get("id", "")
    timestamp = messaging_event.get("timestamp", "0")
    event_id = f"message_{page_id}_{mid or sender_id}_{timestamp}"

    return build_raw_event(
        event_id=event_id,
        event_type="message_created",
        page_id=page_id,
        message=text,
        user_id=sender_id,
        message_id=mid,
        channel="messenger",
        raw_payload=messaging_event,
    )


def normalize_entry(entry):
    page_id = entry.get("id")
    if not page_id:
        return []

    events = []
    for change in entry.get("changes", []):
        normalized = normalize_feed_change(page_id, change)
        if normalized:
            events.append(normalized)

    for messaging_event in entry.get("messaging", []):
        normalized = normalize_messaging_event(page_id, messaging_event)
        if normalized:
            events.append(normalized)

    return events


def normalize_webhook_payload(payload):
    if payload.get("object") not in {"page", "instagram"}:
        return []

    events = []
    for entry in payload.get("entry", []):
        events.extend(normalize_entry(entry))
    return events
