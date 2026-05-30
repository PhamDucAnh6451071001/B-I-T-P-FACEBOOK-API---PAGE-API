from django.db import models


class IdempotencyKey(models.Model):
    command_id = models.CharField(max_length=100, unique=True)
    event_id = models.CharField(max_length=100, blank=True)
    source_topic = models.CharField(max_length=50)
    status = models.CharField(max_length=20, default="processed")
    processed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "idempotency_keys"

    def __str__(self):
        return self.command_id


class InboundEvent(models.Model):
    STATUS_CHOICES = [
        ("received", "Received"),
        ("processing", "Processing"),
        ("processed", "Processed"),
        ("pending_review", "Pending Review"),
        ("blacklisted", "Blacklisted"),
        ("rate_limited", "Rate Limited"),
        ("spam_hidden", "Spam Hidden"),
        ("duplicate", "Duplicate"),
    ]

    event_id = models.CharField(max_length=200, unique=True)
    event_type = models.CharField(max_length=50)
    channel = models.CharField(max_length=20)
    page_id = models.CharField(max_length=50)
    user_id = models.CharField(max_length=50, blank=True)
    message = models.TextField(blank=True)
    post_id = models.CharField(max_length=100, null=True, blank=True)
    comment_id = models.CharField(max_length=100, null=True, blank=True)
    message_id = models.CharField(max_length=100, null=True, blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="received")
    intent = models.CharField(max_length=50, blank=True)
    sentiment = models.CharField(max_length=20, blank=True)
    action = models.CharField(max_length=30, blank=True)
    command_id = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "inbound_events"
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["user_id", "page_id", "created_at"]),
        ]

    def __str__(self):
        return self.event_id


class UserBlacklist(models.Model):
    user_id = models.CharField(max_length=50)
    page_id = models.CharField(max_length=50)
    reason = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "user_blacklist"
        unique_together = [("user_id", "page_id")]

    def __str__(self):
        return f"{self.user_id}@{self.page_id}"


class UserMessageFingerprint(models.Model):
    user_id = models.CharField(max_length=50)
    page_id = models.CharField(max_length=50)
    content_hash = models.CharField(max_length=64)
    repeat_count = models.PositiveIntegerField(default=1)
    last_seen_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_message_fingerprints"
        unique_together = [("user_id", "page_id", "content_hash")]

    def __str__(self):
        return f"{self.user_id}:{self.content_hash[:8]}"


class CommentHistory(models.Model):
    command_id = models.CharField(max_length=120)
    event_id = models.CharField(max_length=200, blank=True)
    page_id = models.CharField(max_length=50, blank=True)
    user_id = models.CharField(max_length=50, blank=True)
    comment_id = models.CharField(max_length=100, null=True, blank=True)
    message_id = models.CharField(max_length=100, null=True, blank=True)
    channel = models.CharField(max_length=20, blank=True)
    action = models.CharField(max_length=30, blank=True)
    user_message = models.TextField(blank=True)
    reply_text = models.TextField(blank=True)
    status = models.CharField(max_length=30, default="processed")
    source_topic = models.CharField(max_length=50, blank=True)
    facebook_response = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "comment_history"
        indexes = [
            models.Index(fields=["page_id", "created_at"]),
            models.Index(fields=["comment_id", "created_at"]),
            models.Index(fields=["command_id"]),
        ]

    def __str__(self):
        return self.command_id

