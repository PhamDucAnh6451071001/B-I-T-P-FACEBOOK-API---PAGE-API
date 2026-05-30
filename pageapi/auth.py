import hmac

from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import BasePermission


class AdminUser:
    is_authenticated = True
    is_staff = True
    is_active = True

    @property
    def pk(self):
        return "admin"


class AdminTokenAuthentication(BaseAuthentication):
    keyword = "X-Admin-Token"
    www_authenticate_realm = "Admin API"

    def authenticate(self, request):
        expected = getattr(settings, "ADMIN_API_TOKEN", "")
        if not expected:
            raise AuthenticationFailed("ADMIN_API_TOKEN is not configured on server")

        token = request.headers.get(self.keyword, "")
        if not token or not hmac.compare_digest(token, expected):
            raise AuthenticationFailed("Invalid or missing admin token")

        return (AdminUser(), token)

    def authenticate_header(self, request):
        return self.keyword


class IsAdminUser(BasePermission):
    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        return bool(user and getattr(user, "is_authenticated", False))
