from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("pageapi", "0001_idempotency_keys"),
    ]

    operations = [
        migrations.CreateModel(
            name="InboundEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event_id", models.CharField(max_length=200, unique=True)),
                ("event_type", models.CharField(max_length=50)),
                ("channel", models.CharField(max_length=20)),
                ("page_id", models.CharField(max_length=50)),
                ("user_id", models.CharField(blank=True, max_length=50)),
                ("message", models.TextField(blank=True)),
                ("post_id", models.CharField(blank=True, max_length=100, null=True)),
                ("comment_id", models.CharField(blank=True, max_length=100, null=True)),
                ("message_id", models.CharField(blank=True, max_length=100, null=True)),
                ("status", models.CharField(default="received", max_length=30)),
                ("intent", models.CharField(blank=True, max_length=50)),
                ("sentiment", models.CharField(blank=True, max_length=20)),
                ("action", models.CharField(blank=True, max_length=30)),
                ("command_id", models.CharField(blank=True, max_length=120)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("processed_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={"db_table": "inbound_events"},
        ),
        migrations.CreateModel(
            name="UserBlacklist",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("user_id", models.CharField(max_length=50)),
                ("page_id", models.CharField(max_length=50)),
                ("reason", models.CharField(max_length=100)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "db_table": "user_blacklist",
                "unique_together": {("user_id", "page_id")},
            },
        ),
        migrations.CreateModel(
            name="UserMessageFingerprint",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("user_id", models.CharField(max_length=50)),
                ("page_id", models.CharField(max_length=50)),
                ("content_hash", models.CharField(max_length=64)),
                ("repeat_count", models.PositiveIntegerField(default=1)),
                ("last_seen_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "user_message_fingerprints",
                "unique_together": {("user_id", "page_id", "content_hash")},
            },
        ),
        migrations.AddIndex(
            model_name="inboundevent",
            index=models.Index(fields=["status", "created_at"], name="inbound_ev_status_0a1b2c_idx"),
        ),
        migrations.AddIndex(
            model_name="inboundevent",
            index=models.Index(fields=["user_id", "page_id", "created_at"], name="inbound_ev_user_id_3d4e5f_idx"),
        ),
    ]
