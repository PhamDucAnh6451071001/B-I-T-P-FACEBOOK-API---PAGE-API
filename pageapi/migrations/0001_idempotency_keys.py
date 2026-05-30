from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="IdempotencyKey",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("command_id", models.CharField(max_length=100, unique=True)),
                ("event_id", models.CharField(blank=True, max_length=100)),
                ("source_topic", models.CharField(max_length=50)),
                ("status", models.CharField(default="processed", max_length=20)),
                ("processed_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"db_table": "idempotency_keys"},
        ),
    ]
