import unittest
from unittest.mock import patch

from shared.retry_handler import compute_backoff_seconds, process_failed_message


class RetryHandlerTests(unittest.TestCase):
    def setUp(self):
        self.failed = {
            "schema_version": 1,
            "command_id": "cmd_001",
            "event_id": "evt_001",
            "retry_count": 0,
            "last_error": "Facebook timeout",
            "payload": {"reply_text": "hello"},
            "target": {"comment_id": "cmt_001"},
            "action": "reply",
        }
        self.retries = []
        self.dlq = []

    def test_backoff_formula(self):
        self.assertEqual(compute_backoff_seconds(1), 1)
        self.assertEqual(compute_backoff_seconds(2), 2)
        self.assertEqual(compute_backoff_seconds(3), 4)

    @patch("shared.retry_handler.time.sleep")
    def test_publish_retry_within_max(self, _sleep):
        outcome = process_failed_message(
            self.failed,
            max_retry=3,
            publish_retry=self.retries.append,
            publish_dlq=self.dlq.append,
            sleep_fn=lambda _seconds: None,
        )
        self.assertEqual(outcome["result"], "retry")
        self.assertEqual(outcome["retry_count"], 1)
        self.assertEqual(len(self.retries), 1)
        self.assertEqual(len(self.dlq), 0)
        self.assertEqual(self.retries[0]["retry_count"], 1)

    @patch("shared.retry_handler.time.sleep")
    def test_publish_dlq_after_max_retry(self, _sleep):
        failed = {**self.failed, "retry_count": 3}
        outcome = process_failed_message(
            failed,
            max_retry=3,
            publish_retry=self.retries.append,
            publish_dlq=self.dlq.append,
            sleep_fn=lambda _seconds: None,
        )
        self.assertEqual(outcome["result"], "dlq")
        self.assertEqual(outcome["retry_count"], 4)
        self.assertEqual(len(self.retries), 0)
        self.assertEqual(len(self.dlq), 1)
        self.assertEqual(self.dlq[0]["final_error"], "Facebook timeout")


if __name__ == "__main__":
    unittest.main()
