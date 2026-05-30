import requests
from django.conf import settings
from pageapi.circuit_breaker import SimpleCircuitBreaker

GRAPH_BASE_URL = f"https://graph.facebook.com/{settings.FB_GRAPH_VERSION}"
facebook_breaker = SimpleCircuitBreaker(
    failure_threshold=int(getattr(settings, "FACEBOOK_BREAKER_FAILURE_THRESHOLD", 5)),
    recovery_seconds=int(getattr(settings, "FACEBOOK_BREAKER_RECOVERY_SECONDS", 30)),
)


def graph_get(path, params=None):
    params = params or {}
    params["access_token"] = settings.FB_PAGE_ACCESS_TOKEN
    return requests.get(f"{GRAPH_BASE_URL}/{path}", params=params, timeout=15)


def graph_post(path, data=None):
    data = data or {}
    data["access_token"] = settings.FB_PAGE_ACCESS_TOKEN
    return requests.post(f"{GRAPH_BASE_URL}/{path}", data=data, timeout=15)


def graph_delete(path):
    params = {"access_token": settings.FB_PAGE_ACCESS_TOKEN}
    return requests.delete(f"{GRAPH_BASE_URL}/{path}", params=params, timeout=15)


def send_action_to_facebook(command):
    if not facebook_breaker.allow_request():
        raise RuntimeError("Circuit breaker is OPEN for Facebook API")

    action = command["action"]
    payload = command.get("payload", {})
    target = command.get("target", {})

    if action == "reply":
        channel = target.get("channel", "comment")
        reply_text = payload.get("reply_text")
        if channel == "messenger":
            page_id = target.get("page_id")
            user_id = target.get("user_id")
            if not page_id or not user_id or not reply_text:
                raise ValueError("messenger reply requires target.page_id, target.user_id and payload.reply_text")
            response = graph_post(
                f"{page_id}/messages",
                {
                    "recipient": {"id": user_id},
                    "message": {"text": reply_text},
                },
            )
        else:
            comment_id = target.get("comment_id")
            if not comment_id or not reply_text:
                raise ValueError("reply action requires target.comment_id and payload.reply_text")
            response = graph_post(f"{comment_id}/comments", {"message": reply_text})
    elif action == "hide":
        comment_id = target.get("comment_id")
        if not comment_id:
            raise ValueError("hide action requires target.comment_id")
        response = graph_post(f"{comment_id}", {"is_hidden": "true"})
    elif action == "post":
        page_id = target.get("page_id")
        message = payload.get("message")
        if not page_id or not message:
            raise ValueError("post action requires target.page_id and payload.message")
        response = graph_post(f"{page_id}/feed", {"message": message})
    elif action == "escalate_admin":
        return {"status": "escalated_to_admin", "note": "Event queued for admin review"}
    else:
        raise ValueError(f"Unsupported action: {action}")

    if response.status_code >= 400:
        facebook_breaker.on_failure()
        raise RuntimeError(f"Facebook API error {response.status_code}: {response.text}")

    facebook_breaker.on_success()
    return response.json()
