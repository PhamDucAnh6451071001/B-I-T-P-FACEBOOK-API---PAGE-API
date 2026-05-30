import os
from contextlib import contextmanager

import psycopg2
import psycopg2.extras

EVENT_STATUS_RECEIVED = "received"
EVENT_STATUS_PROCESSING = "processing"
EVENT_STATUS_PROCESSED = "processed"
EVENT_STATUS_PENDING_REVIEW = "pending_review"
EVENT_STATUS_BLACKLISTED = "blacklisted"
EVENT_STATUS_RATE_LIMITED = "rate_limited"
EVENT_STATUS_SPAM = "spam_hidden"
EVENT_STATUS_DUPLICATE = "duplicate"


def _db_config():
    return {
        "dbname": os.getenv("POSTGRES_DB", "fb_api_db"),
        "user": os.getenv("POSTGRES_USER", "fb_api_user"),
        "password": os.getenv("POSTGRES_PASSWORD", "fb_api_password"),
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": os.getenv("POSTGRES_PORT", "5432"),
    }


@contextmanager
def db_connection():
    conn = psycopg2.connect(**_db_config())
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def is_user_blacklisted(conn, user_id, page_id):
    if not user_id:
        return False
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1 FROM user_blacklist
            WHERE user_id = %s AND page_id = %s
            LIMIT 1
            """,
            (user_id, page_id),
        )
        return cur.fetchone() is not None


def add_user_to_blacklist(conn, user_id, page_id, reason):
    if not user_id:
        return
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO user_blacklist (user_id, page_id, reason, created_at)
            VALUES (%s, %s, %s, NOW())
            ON CONFLICT (user_id, page_id) DO NOTHING
            """,
            (user_id, page_id, reason),
        )


def count_recent_user_events(conn, user_id, page_id, window_seconds):
    if not user_id:
        return 0
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT COUNT(*) FROM inbound_events
            WHERE user_id = %s AND page_id = %s
              AND created_at >= NOW() - (%s * INTERVAL '1 second')
            """,
            (user_id, page_id, window_seconds),
        )
        return int(cur.fetchone()[0])


def record_message_fingerprint(conn, user_id, page_id, content_hash):
    if not user_id:
        return 1
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO user_message_fingerprints
                (user_id, page_id, content_hash, repeat_count, last_seen_at)
            VALUES (%s, %s, %s, 1, NOW())
            ON CONFLICT (user_id, page_id, content_hash)
            DO UPDATE SET
                repeat_count = user_message_fingerprints.repeat_count + 1,
                last_seen_at = NOW()
            RETURNING repeat_count
            """,
            (user_id, page_id, content_hash),
        )
        return int(cur.fetchone()[0])


def create_inbound_event(conn, event):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO inbound_events (
                event_id, event_type, channel, page_id, user_id, message,
                post_id, comment_id, message_id, status, intent, sentiment, action,
                command_id, created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT (event_id) DO NOTHING
            RETURNING status
            """,
            (
                event["event_id"],
                event.get("event_type", ""),
                event.get("channel", ""),
                event.get("page_id", ""),
                event.get("user_id", ""),
                event.get("message", ""),
                event.get("post_id"),
                event.get("comment_id"),
                event.get("message_id"),
                EVENT_STATUS_RECEIVED,
                "",
                "",
                "",
                "",
            ),
        )
        row = cur.fetchone()
        if row:
            return "created", row[0]
        cur.execute("SELECT status FROM inbound_events WHERE event_id = %s", (event["event_id"],))
        existing = cur.fetchone()
        return "duplicate", existing[0] if existing else EVENT_STATUS_DUPLICATE


def update_event_status(
    conn,
    event_id,
    status,
    *,
    intent="",
    sentiment="",
    action="",
    command_id="",
):
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE inbound_events
            SET status = %s,
                intent = %s,
                sentiment = %s,
                action = %s,
                command_id = %s,
                processed_at = CASE WHEN %s IN (%s, %s, %s, %s, %s, %s) THEN NOW() ELSE processed_at END
            WHERE event_id = %s
            """,
            (
                status,
                intent,
                sentiment,
                action,
                command_id,
                status,
                EVENT_STATUS_PROCESSED,
                EVENT_STATUS_PENDING_REVIEW,
                EVENT_STATUS_BLACKLISTED,
                EVENT_STATUS_RATE_LIMITED,
                EVENT_STATUS_SPAM,
                EVENT_STATUS_DUPLICATE,
                event_id,
            ),
        )
