import requests
from django.conf import settings
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema

GRAPH_BASE_URL = f"https://graph.facebook.com/{settings.FB_GRAPH_VERSION}"


def graph_get(path, params=None):
    if params is None:
        params = {}
    params["access_token"] = settings.FB_PAGE_ACCESS_TOKEN
    response = requests.get(f"{GRAPH_BASE_URL}/{path}", params=params, timeout=15)
    return response


def graph_post(path, data=None):
    if data is None:
        data = {}
    data["access_token"] = settings.FB_PAGE_ACCESS_TOKEN
    response = requests.post(f"{GRAPH_BASE_URL}/{path}", data=data, timeout=15)
    return response


def graph_delete(path):
    params = {"access_token": settings.FB_PAGE_ACCESS_TOKEN}
    response = requests.delete(f"{GRAPH_BASE_URL}/{path}", params=params, timeout=15)
    return response


@extend_schema(
    summary="Lấy thông tin Page",
    responses={200: dict},
)
@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def get_page_info(request, page_id):
    response = graph_get(
        f"{page_id}",
        {"fields": "id,name,about,fan_count,followers_count,link,picture"}
    )
    return Response(response.json(), status=response.status_code)


@extend_schema(
    summary="Lấy danh sách bài viết hoặc tạo bài viết mới",
    request={
        "application/json": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "example": "Hello from Django Swagger"
                }
            },
            "required": ["message"]
        }
    },
    responses={200: dict},
)
@api_view(["GET", "POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def page_posts(request, page_id):
    if request.method == "GET":
        response = graph_get(
            f"{page_id}/feed",
            {"fields": "id,message,created_time,permalink_url,full_picture"}
        )
        return Response(response.json(), status=response.status_code)

    message = request.data.get("message")
    if not message:
        return Response(
            {"error": {"message": "message is required"}},
            status=status.HTTP_400_BAD_REQUEST
        )

    response = graph_post(
        f"{page_id}/feed",
        {"message": message}
    )
    return Response(response.json(), status=response.status_code)


@extend_schema(
    summary="Xóa bài viết",
    responses={200: dict},
)
@api_view(["DELETE"])
@authentication_classes([])
@permission_classes([AllowAny])
def delete_page_post(request, post_id):
    response = graph_delete(f"{post_id}")
    return Response(response.json(), status=response.status_code)


@extend_schema(
    summary="Lấy comments của bài viết",
    responses={200: dict},
)
@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def get_post_comments(request, post_id):
    response = graph_get(
        f"{post_id}/comments",
        {"fields": "id,message,from,created_time"}
    )
    return Response(response.json(), status=response.status_code)


@extend_schema(
    summary="Lấy likes/reactions của bài viết",
    responses={200: dict},
)
@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def get_post_likes(request, post_id):
    response = graph_get(
        f"{post_id}/reactions",
        {"summary": "true"}
    )
    return Response(
        {
            "note": "Facebook Graph API hiện tại dùng reactions thay cho likes edge cũ",
            "result": response.json()
        },
        status=response.status_code
    )


@extend_schema(
    summary="Lấy insights của Page",
    responses={200: dict},
)
@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def get_page_insights(request, page_id):
    # hard-code metric và period để Swagger không cần nhập
    response = graph_get(
        f"{page_id}/insights",
        {
            "metric": "page_views_total",
            "period": "day",
        }
    )
    return Response(response.json(), status=response.status_code)