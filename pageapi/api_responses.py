import requests
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed, NotAuthenticated, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler


def api_success(data, status_code=status.HTTP_200_OK, meta=None):
    payload = {"success": True, "data": data}
    if meta:
        payload["meta"] = meta
    return Response(payload, status=status_code)


def api_error(code, message, status_code, details=None):
    error = {"code": code, "message": message}
    if details is not None:
        error["details"] = details
    return Response({"success": False, "error": error}, status=status_code)


def from_facebook_response(response):
    try:
        body = response.json()
    except ValueError:
        return api_error(
            "FACEBOOK_INVALID_JSON",
            "Invalid JSON response from Facebook Graph API",
            status.HTTP_502_BAD_GATEWAY,
            details={"raw": response.text[:500]},
        )

    if response.status_code >= 400:
        fb_error = body.get("error", body)
        return api_error(
            fb_error.get("type", "FACEBOOK_API_ERROR"),
            fb_error.get("message", "Facebook Graph API request failed"),
            response.status_code,
            details={
                "facebook_code": fb_error.get("code"),
                "facebook_subcode": fb_error.get("error_subcode"),
                "fbtrace_id": fb_error.get("fbtrace_id"),
            },
        )

    return api_success(body, response.status_code, meta={"source": "facebook_graph_api"})


def handle_facebook_request(request_fn):
    try:
        response = request_fn()
    except requests.Timeout:
        return api_error(
            "FACEBOOK_TIMEOUT",
            "Facebook Graph API request timed out",
            status.HTTP_504_GATEWAY_TIMEOUT,
        )
    except requests.RequestException as exc:
        return api_error(
            "NETWORK_ERROR",
            "Unable to reach Facebook Graph API",
            status.HTTP_502_BAD_GATEWAY,
            details={"reason": str(exc)},
        )

    return from_facebook_response(response)


def custom_exception_handler(exc, context):
    if isinstance(exc, (AuthenticationFailed, NotAuthenticated)):
        return api_error(
            "UNAUTHORIZED",
            str(exc.detail if hasattr(exc, "detail") else exc),
            status.HTTP_401_UNAUTHORIZED,
        )

    if isinstance(exc, PermissionDenied):
        return api_error(
            "FORBIDDEN",
            str(exc.detail if hasattr(exc, "detail") else exc),
            status.HTTP_403_FORBIDDEN,
        )

    response = exception_handler(exc, context)
    if response is None:
        return None

    if isinstance(exc, ValidationError):
        details = response.data
        message = "Validation failed"
        if isinstance(details, dict) and "non_field_errors" in details:
            message = str(details["non_field_errors"][0])
        elif isinstance(details, list) and details:
            message = str(details[0])
        return api_error("VALIDATION_ERROR", message, response.status_code, details=details)

    message = "Request failed"
    details = response.data
    if isinstance(details, dict):
        message = details.get("detail", message)
    elif isinstance(details, list) and details:
        message = str(details[0])

    return api_error("API_ERROR", str(message), response.status_code, details=details)
