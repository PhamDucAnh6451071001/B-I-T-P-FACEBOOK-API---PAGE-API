from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema
from pageapi.api_responses import api_error, api_success, handle_facebook_request
from pageapi.auth import AdminTokenAuthentication, IsAdminUser
from pageapi.facebook_client import graph_delete, graph_get, graph_post
from pageapi.models import CommentHistory, InboundEvent, UserBlacklist

ADMIN_AUTH = [AdminTokenAuthentication]
ADMIN_PERM = [IsAdminUser]


@extend_schema(summary="Health check", responses={200: dict})
@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def health_check(request):
    return Response({"status": "ok", "service": "backend-api"}, status=status.HTTP_200_OK)


@extend_schema(summary="Lay thong tin Page", responses={200: dict})
@api_view(["GET"])
@authentication_classes(ADMIN_AUTH)
@permission_classes(ADMIN_PERM)
def get_page_info(request, page_id):
    return handle_facebook_request(
        lambda: graph_get(
            f"{page_id}",
            {"fields": "id,name,about,fan_count,followers_count,link,picture"},
        )
    )


@extend_schema(
    summary="Lay danh sach bai viet hoac tao bai viet moi",
    request={
        "application/json": {
            "type": "object",
            "properties": {"message": {"type": "string", "example": "Hello from Django Swagger"}},
            "required": ["message"],
        }
    },
    responses={200: dict},
)
@api_view(["GET", "POST"])
@authentication_classes(ADMIN_AUTH)
@permission_classes(ADMIN_PERM)
def page_posts(request, page_id):
    if request.method == "GET":
        return handle_facebook_request(
            lambda: graph_get(
                f"{page_id}/feed",
                {"fields": "id,message,created_time,permalink_url,full_picture"},
            )
        )

    message = request.data.get("message")
    if not message:
        return api_error(
            "VALIDATION_ERROR",
            "message is required",
            status.HTTP_400_BAD_REQUEST,
            details={"field": "message"},
        )

    return handle_facebook_request(lambda: graph_post(f"{page_id}/feed", {"message": message}))


@extend_schema(summary="Xoa bai viet", responses={200: dict})
@api_view(["DELETE"])
@authentication_classes(ADMIN_AUTH)
@permission_classes(ADMIN_PERM)
def delete_page_post(request, post_id):
    return handle_facebook_request(lambda: graph_delete(f"{post_id}"))


@extend_schema(summary="Lay comments cua bai viet", responses={200: dict})
@api_view(["GET"])
@authentication_classes(ADMIN_AUTH)
@permission_classes(ADMIN_PERM)
def get_post_comments(request, post_id):
    return handle_facebook_request(
        lambda: graph_get(
            f"{post_id}/comments",
            {"fields": "id,message,from,created_time"},
        )
    )


@extend_schema(summary="Lay likes/reactions cua bai viet", responses={200: dict})
@api_view(["GET"])
@authentication_classes(ADMIN_AUTH)
@permission_classes(ADMIN_PERM)
def get_post_likes(request, post_id):
    response = handle_facebook_request(
        lambda: graph_get(f"{post_id}/reactions", {"summary": "true"})
    )
    if hasattr(response, "data") and response.data.get("success"):
        response.data["meta"] = {
            "source": "facebook_graph_api",
            "note": "Facebook Graph API dung reactions edge thay cho likes cu",
        }
    return response


@extend_schema(summary="Lay insights cua Page", responses={200: dict})
@api_view(["GET"])
@authentication_classes(ADMIN_AUTH)
@permission_classes(ADMIN_PERM)
def get_page_insights(request, page_id):
    return handle_facebook_request(
        lambda: graph_get(
            f"{page_id}/insights",
            {"metric": "page_views_total", "period": "day"},
        )
    )


@extend_schema(summary="Danh sach event da xu ly / pending review")
@api_view(["GET"])
@authentication_classes(ADMIN_AUTH)
@permission_classes(ADMIN_PERM)
def list_inbound_events(request):
    status_filter = request.query_params.get("status")
    queryset = InboundEvent.objects.all().order_by("-created_at")
    if status_filter:
        queryset = queryset.filter(status=status_filter)

    data = [
        {
            "event_id": item.event_id,
            "event_type": item.event_type,
            "channel": item.channel,
            "page_id": item.page_id,
            "user_id": item.user_id,
            "message": item.message,
            "status": item.status,
            "intent": item.intent,
            "sentiment": item.sentiment,
            "action": item.action,
            "command_id": item.command_id,
            "created_at": item.created_at,
            "processed_at": item.processed_at,
        }
        for item in queryset[:100]
    ]
    return api_success({"count": len(data), "results": data}, meta={"source": "inbound_events"})


@extend_schema(summary="Danh sach user blacklist")
@api_view(["GET"])
@authentication_classes(ADMIN_AUTH)
@permission_classes(ADMIN_PERM)
def list_blacklist(request):
    page_id = request.query_params.get("page_id")
    queryset = UserBlacklist.objects.all().order_by("-created_at")
    if page_id:
        queryset = queryset.filter(page_id=page_id)

    data = [
        {
            "user_id": item.user_id,
            "page_id": item.page_id,
            "reason": item.reason,
            "created_at": item.created_at,
        }
        for item in queryset[:200]
    ]
    return api_success({"count": len(data), "results": data}, meta={"source": "user_blacklist"})


@extend_schema(summary="Lich su comment/message da xu ly")
@api_view(["GET"])
@authentication_classes(ADMIN_AUTH)
@permission_classes(ADMIN_PERM)
def list_comment_history(request):
    page_id = request.query_params.get("page_id")
    status_filter = request.query_params.get("status")
    queryset = CommentHistory.objects.all().order_by("-created_at")
    if page_id:
        queryset = queryset.filter(page_id=page_id)
    if status_filter:
        queryset = queryset.filter(status=status_filter)

    data = [
        {
            "command_id": item.command_id,
            "event_id": item.event_id,
            "page_id": item.page_id,
            "user_id": item.user_id,
            "comment_id": item.comment_id,
            "message_id": item.message_id,
            "channel": item.channel,
            "action": item.action,
            "user_message": item.user_message,
            "reply_text": item.reply_text,
            "status": item.status,
            "source_topic": item.source_topic,
            "facebook_response": item.facebook_response,
            "created_at": item.created_at,
        }
        for item in queryset[:200]
    ]
    return api_success({"count": len(data), "results": data}, meta={"source": "comment_history"})


def _parse_block_payload(request):
    user_id = request.data.get("user_id") or request.query_params.get("user_id")
    page_id = request.data.get("page_id") or request.query_params.get("page_id")
    reason = request.data.get("reason") or request.query_params.get("reason") or "manual_admin"
    return user_id, page_id, reason


@extend_schema(summary="Block user thu cong (blacklist)")
@api_view(["POST"])
@authentication_classes(ADMIN_AUTH)
@permission_classes(ADMIN_PERM)
def block_user(request):
    user_id, page_id, reason = _parse_block_payload(request)
    if not user_id or not page_id:
        return api_error(
            "VALIDATION_ERROR",
            "user_id and page_id are required",
            status.HTTP_400_BAD_REQUEST,
            details={"required": ["user_id", "page_id"]},
        )

    item, created = UserBlacklist.objects.get_or_create(
        user_id=user_id,
        page_id=page_id,
        defaults={"reason": reason},
    )
    if not created and reason:
        item.reason = reason
        item.save(update_fields=["reason"])

    return api_success(
        {
            "user_id": item.user_id,
            "page_id": item.page_id,
            "reason": item.reason,
            "blocked": True,
            "created": created,
        },
        status_code=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        meta={"source": "user_blacklist"},
    )


@extend_schema(summary="Unblock user (xoa khoi blacklist)")
@api_view(["DELETE"])
@authentication_classes(ADMIN_AUTH)
@permission_classes(ADMIN_PERM)
def unblock_user(request):
    user_id, page_id, _ = _parse_block_payload(request)
    if not user_id or not page_id:
        return api_error(
            "VALIDATION_ERROR",
            "user_id and page_id are required",
            status.HTTP_400_BAD_REQUEST,
            details={"required": ["user_id", "page_id"]},
        )

    deleted_count, _ = UserBlacklist.objects.filter(user_id=user_id, page_id=page_id).delete()
    if deleted_count == 0:
        return api_error(
            "NOT_FOUND",
            "User is not in blacklist",
            status.HTTP_404_NOT_FOUND,
            details={"user_id": user_id, "page_id": page_id},
        )

    return api_success(
        {"user_id": user_id, "page_id": page_id, "blocked": False},
        meta={"source": "user_blacklist"},
    )


@extend_schema(summary="Them user vao blacklist (alias)", deprecated=True)
@api_view(["POST"])
@authentication_classes(ADMIN_AUTH)
@permission_classes(ADMIN_PERM)
def add_blacklist_user(request):
    return block_user(request)
