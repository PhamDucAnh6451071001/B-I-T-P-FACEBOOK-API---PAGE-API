from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from pageapi.kafka_processing import process_command
from pageapi.models import IdempotencyKey, UserBlacklist


@override_settings(ADMIN_API_TOKEN="test-admin-token")
class AdminAuthenticationTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_health_is_public(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["service"], "backend-api")

    def test_dashboard_requires_admin_token(self):
        response = self.client.get("/api/page/123")
        self.assertEqual(response.status_code, 401)
        self.assertFalse(response.json()["success"])
        self.assertEqual(response.json()["error"]["code"], "UNAUTHORIZED")

    @patch("pageapi.views.graph_get")
    def test_dashboard_with_valid_admin_token(self, mocked_graph_get):
        mocked_graph_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"id": "123", "name": "Demo Page"},
        )
        response = self.client.get(
            "/api/page/123",
            HTTP_X_ADMIN_TOKEN="test-admin-token",
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        self.assertEqual(body["data"]["id"], "123")
        self.assertEqual(body["meta"]["source"], "facebook_graph_api")

    @patch("pageapi.views.graph_get")
    def test_facebook_error_is_normalized(self, mocked_graph_get):
        mocked_graph_get.return_value = MagicMock(
            status_code=400,
            json=lambda: {
                "error": {
                    "message": "Invalid OAuth access token.",
                    "type": "OAuthException",
                    "code": 190,
                    "fbtrace_id": "abc123",
                }
            },
        )
        response = self.client.get(
            "/api/page/123",
            HTTP_X_ADMIN_TOKEN="test-admin-token",
        )
        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertFalse(body["success"])
        self.assertEqual(body["error"]["code"], "OAuthException")
        self.assertEqual(body["error"]["details"]["facebook_code"], 190)


@override_settings(ADMIN_API_TOKEN="test-admin-token")
class BlockUserApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_block_user_requires_auth(self):
        response = self.client.post(
            "/api/admin/users/block",
            {"user_id": "u1", "page_id": "p1"},
            format="json",
        )
        self.assertEqual(response.status_code, 401)

    def test_block_and_unblock_user(self):
        headers = {"HTTP_X_ADMIN_TOKEN": "test-admin-token"}

        create_response = self.client.post(
            "/api/admin/users/block",
            {"user_id": "user_001", "page_id": "page_001", "reason": "manual_admin"},
            format="json",
            **headers,
        )
        self.assertEqual(create_response.status_code, 201)
        body = create_response.json()
        self.assertTrue(body["success"])
        self.assertTrue(body["data"]["blocked"])
        self.assertTrue(UserBlacklist.objects.filter(user_id="user_001", page_id="page_001").exists())

        list_response = self.client.get("/api/admin/blacklist", **headers)
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json()["data"]["count"], 1)

        delete_response = self.client.delete(
            "/api/admin/users/unblock?user_id=user_001&page_id=page_001",
            **headers,
        )
        self.assertEqual(delete_response.status_code, 200)
        self.assertFalse(delete_response.json()["data"]["blocked"])
        self.assertFalse(UserBlacklist.objects.filter(user_id="user_001", page_id="page_001").exists())


class KafkaProcessingTests(TestCase):
    def setUp(self):
        self.command = {
            "schema_version": 1,
            "command_id": "cmd_001",
            "event_id": "evt_001",
            "action": "reply",
            "target": {"comment_id": "cmt_001", "page_id": "123"},
            "payload": {"reply_text": "hello", "message": "hello"},
            "created_at": "2026-04-26T09:31:00Z",
            "retry_count": 0,
        }

    @patch("pageapi.kafka_processing.send_action_to_facebook")
    def test_duplicate_command_is_skipped(self, mocked_fb):
        IdempotencyKey.objects.create(
            command_id="cmd_001", event_id="evt_001", source_topic="reply_commands", status="processed"
        )
        failed_messages = []
        result = process_command(self.command, "reply_commands", failed_messages.append)
        self.assertEqual(result["status"], "skipped_duplicate")
        mocked_fb.assert_not_called()

    @patch("pageapi.kafka_processing.send_action_to_facebook")
    def test_failure_publishes_send_failed(self, mocked_fb):
        mocked_fb.side_effect = RuntimeError("Facebook timeout")
        failed_messages = []
        result = process_command(self.command, "reply_commands", failed_messages.append)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(len(failed_messages), 1)
        self.assertEqual(failed_messages[0]["command_id"], "cmd_001")

    @patch("pageapi.kafka_processing.send_action_to_facebook")
    def test_success_records_comment_history(self, mocked_fb):
        mocked_fb.return_value = {"id": "reply_001"}
        process_command(self.command, "reply_commands", lambda _msg: None)
        from pageapi.models import CommentHistory

        history = CommentHistory.objects.get(command_id="cmd_001")
        self.assertEqual(history.status, "processed")
        self.assertEqual(history.reply_text, "hello")
