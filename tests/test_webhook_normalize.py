import unittest

from shared.webhook_normalize import normalize_webhook_payload


class WebhookNormalizeTests(unittest.TestCase):
    def test_normalize_comment_event(self):
        payload = {
            "object": "page",
            "entry": [
                {
                    "id": "1042333895638842",
                    "changes": [
                        {
                            "field": "feed",
                            "value": {
                                "verb": "add",
                                "created_time": 1710000001,
                                "post_id": "post_001",
                                "comment_id": "cmt_001",
                                "message": "Shop oi gia bao nhieu",
                                "from": {"id": "user_001"},
                            },
                        }
                    ],
                }
            ],
        }
        events = normalize_webhook_payload(payload)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event_type"], "comment_created")
        self.assertEqual(events[0]["channel"], "comment")
        self.assertEqual(events[0]["comment_id"], "cmt_001")
        self.assertIsNone(events[0]["message_id"])

    def test_normalize_messenger_event(self):
        payload = {
            "object": "page",
            "entry": [
                {
                    "id": "1042333895638842",
                    "messaging": [
                        {
                            "sender": {"id": "user_002"},
                            "recipient": {"id": "1042333895638842"},
                            "timestamp": 1710000002,
                            "message": {"mid": "m_001", "text": "Xin chao shop"},
                        }
                    ],
                }
            ],
        }
        events = normalize_webhook_payload(payload)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event_type"], "message_created")
        self.assertEqual(events[0]["channel"], "messenger")
        self.assertEqual(events[0]["message_id"], "m_001")
        self.assertIsNone(events[0]["comment_id"])

    def test_normalize_mixed_entry(self):
        payload = {
            "object": "page",
            "entry": [
                {
                    "id": "1042333895638842",
                    "changes": [
                        {
                            "field": "comments",
                            "value": {
                                "verb": "add",
                                "created_time": 1710000003,
                                "comment_id": "cmt_002",
                                "message": "Bai viet hay",
                                "from": {"id": "user_003"},
                            },
                        }
                    ],
                    "messaging": [
                        {
                            "sender": {"id": "user_004"},
                            "timestamp": 1710000004,
                            "message": {"mid": "m_002", "text": "Co ship khong"},
                        }
                    ],
                }
            ],
        }
        events = normalize_webhook_payload(payload)
        self.assertEqual(len(events), 2)
        channels = {event["channel"] for event in events}
        self.assertEqual(channels, {"comment", "messenger"})


if __name__ == "__main__":
    unittest.main()
