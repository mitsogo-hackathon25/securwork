from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cms", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="GlobalSettings",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "order_notification_emails",
                    models.TextField(
                        blank=True,
                        help_text="Comma- or line-separated addresses for new-order alerts only.",
                    ),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Global settings",
                "verbose_name_plural": "Global settings",
            },
        ),
    ]
