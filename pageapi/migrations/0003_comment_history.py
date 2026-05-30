from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("pageapi", "0002_core_processing_tables"),
    ]

    operations = [
        migrations.CreateModel(
            name="CommentHistory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("command_id", models.CharField(max_length=120)),
                ("event_id", models.CharField(blank=True, max_length=200)),
                ("page_id", models.CharField(blank=True, max_length=50)),
                ("user_id", models.CharField(blank=True, max_length=50)),
                ("comment_id", models.CharField(blank=True, max_length=100, null=True)),
                ("message_id", models.CharField(blank=True, max_length=100, null=True)),
                ("channel", models.CharField(blank=True, max_length=20)),
                ("action", models.CharField(blank=True, max_length=30)),
                ("user_message", models.TextField(blank=True)),
                ("reply_text", models.TextField(blank=True)),
                ("status", models.CharField(default="processed", max_length=30)),
                ("source_topic", models.CharField(blank=True, max_length=50)),
                ("facebook_response", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"db_table": "comment_history"},
        ),
        migrations.AddIndex(
            model_name="commenthistory",
            index=models.Index(fields=["page_id", "created_at"], name="comment_hi_page_id_7a8b9c_idx"),
        ),
        migrations.AddIndex(
            model_name="commenthistory",
            index=models.Index(fields=["comment_id", "created_at"], name="comment_hi_comment_1d2e3f_idx"),
        ),
        migrations.AddIndex(
            model_name="commenthistory",
            index=models.Index(fields=["command_id"], name="comment_hi_command_4g5h6i_idx"),
        ),
    ]
