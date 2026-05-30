import unittest
from unittest.mock import patch

from shared.ai_classifier import classify_with_rules
from shared.core_processing import (
    build_reply_command,
    contains_link,
    decide_action,
    hash_message,
    normalize_message,
    process_raw_event,
    should_escalate_to_admin,
)


class CoreProcessingRulesTests(unittest.TestCase):
    def test_link_is_spam(self):
        self.assertTrue(contains_link("xem https://spam.com nhe"))

    def test_classify_price_intent(self):
        intent, sentiment = classify_with_rules("Shop oi gia bao nhieu")
        self.assertEqual(intent, "ask_price")
        self.assertEqual(sentiment, "neutral")

    def test_classify_positive(self):
        intent, sentiment = classify_with_rules("Bai viet hay qua")
        self.assertEqual(intent, "praise")
        self.assertEqual(sentiment, "positive")

    def test_classify_negative_complaint(self):
        intent, sentiment = classify_with_rules("Dich vu te qua")
        self.assertEqual(intent, "complaint")
        self.assertEqual(sentiment, "negative")

    def test_decide_spam_comment_hide(self):
        action, _ = decide_action("spam", "negative", channel="comment", is_spam=True, escalate_admin=False)
        self.assertEqual(action, "hide")

    def test_decide_spam_messenger_escalate(self):
        action, _ = decide_action("spam", "negative", channel="messenger", is_spam=True, escalate_admin=False)
        self.assertEqual(action, "escalate_admin")

    def test_decide_negative_reply(self):
        action, text = decide_action("complaint", "negative", channel="comment", is_spam=False, escalate_admin=False)
        self.assertEqual(action, "reply")
        self.assertIn("xin loi", text.lower())

    def test_decide_positive_reply(self):
        action, text = decide_action("praise", "positive", channel="comment", is_spam=False, escalate_admin=False)
        self.assertEqual(action, "reply")
        self.assertIn("cam on", text.lower())

    def test_escalate_admin_for_refund(self):
        self.assertTrue(should_escalate_to_admin("complaint", "negative", "Toi muon hoan tien"))

    def test_message_hash_is_stable(self):
        self.assertEqual(hash_message("  Hello   World "), hash_message("hello world"))


class CoreProcessingFlowTests(unittest.TestCase):
    def _event(self, **overrides):
        base = {
            "event_id": "evt_test_001",
            "event_type": "comment_created",
            "channel": "comment",
            "page_id": "page_001",
            "user_id": "user_001",
            "message": "Cam on shop",
            "comment_id": "cmt_001",
        }
        base.update(overrides)
        return base

    @patch("shared.core_processing.update_event_status")
    @patch("shared.core_processing.create_inbound_event", return_value=("created", "received"))
    @patch("shared.core_processing.is_user_blacklisted", return_value=False)
    @patch("shared.core_processing.is_rate_limited", return_value=False)
    @patch("shared.core_processing.is_repeated_spam", return_value=False)
    @patch("shared.core_processing.record_message_fingerprint", return_value=1)
    @patch("shared.core_processing.add_user_to_blacklist")
    def test_positive_comment_publishes_reply(
        self,
        _blacklist,
        _fingerprint,
        _repeat,
        _rate,
        _listed,
        _create,
        _update,
    ):
        command, status = process_raw_event(object(), self._event())
        self.assertEqual(status, "processed")
        self.assertEqual(command["action"], "reply")
        self.assertEqual(command["target"]["comment_id"], "cmt_001")

    @patch("shared.core_processing.update_event_status")
    @patch("shared.core_processing.create_inbound_event", return_value=("created", "received"))
    @patch("shared.core_processing.is_user_blacklisted", return_value=False)
    @patch("shared.core_processing.is_rate_limited", return_value=False)
    @patch("shared.core_processing.is_repeated_spam", return_value=True)
    @patch("shared.core_processing.record_message_fingerprint", return_value=3)
    @patch("shared.core_processing.add_user_to_blacklist")
    def test_repeat_spam_hide_and_blacklist(
        self,
        mock_blacklist,
        _fingerprint,
        _repeat,
        _rate,
        _listed,
        _create,
        _update,
    ):
        command, status = process_raw_event(
            object(),
            self._event(message="spam spam spam", user_id="user_spam"),
        )
        self.assertEqual(status, "spam_hidden")
        self.assertEqual(command["action"], "hide")
        mock_blacklist.assert_called_once()

    @patch("shared.core_processing.update_event_status")
    @patch("shared.core_processing.create_inbound_event", return_value=("created", "received"))
    @patch("shared.core_processing.is_user_blacklisted", return_value=True)
    def test_blacklisted_user_skipped(self, _listed, _create, _update):
        command, status = process_raw_event(object(), self._event())
        self.assertIsNone(command)
        self.assertEqual(status, "blacklisted")

    @patch("shared.core_processing.update_event_status")
    @patch("shared.core_processing.create_inbound_event", return_value=("created", "received"))
    @patch("shared.core_processing.is_user_blacklisted", return_value=False)
    @patch("shared.core_processing.is_rate_limited", return_value=True)
    def test_rate_limit_escalates_admin(self, _rate, _listed, _create, _update):
        command, status = process_raw_event(object(), self._event())
        self.assertEqual(status, "pending_review")
        self.assertEqual(command["action"], "escalate_admin")

    @patch("shared.core_processing.update_event_status")
    @patch("shared.core_processing.create_inbound_event", return_value=("duplicate", "processed"))
    def test_duplicate_event_skipped(self, _create, _update):
        command, status = process_raw_event(object(), self._event())
        self.assertIsNone(command)
        self.assertEqual(status, "processed")

    def test_build_reply_command_includes_channel(self):
        command = build_reply_command(
            self._event(channel="messenger", message_id="mid_001"),
            "reply",
            "hello",
            "general",
            "neutral",
        )
        self.assertEqual(command["target"]["channel"], "messenger")
        self.assertEqual(command["target"]["message_id"], "mid_001")


if __name__ == "__main__":
    unittest.main()
