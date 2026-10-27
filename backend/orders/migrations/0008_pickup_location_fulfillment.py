import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0007_order_payment_fee"),
    ]

    operations = [
        migrations.CreateModel(
            name="PickupLocation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=200)),
                ("address", models.CharField(max_length=255)),
                ("city", models.CharField(max_length=100)),
                ("postcode", models.CharField(max_length=20)),
                ("country", models.CharField(default="IT", max_length=2)),
                ("phone", models.CharField(blank=True, max_length=30)),
                ("notes", models.TextField(blank=True, help_text="Opening hours or pickup instructions.")),
                ("is_active", models.BooleanField(default=True)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["sort_order", "name"],
            },
        ),
        migrations.AddField(
            model_name="order",
            name="fulfillment_type",
            field=models.CharField(
                choices=[("delivery", "Consegna"), ("pickup", "Ritiro in sede")],
                default="delivery",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="pickup_location",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="orders",
                to="orders.pickuplocation",
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="pickup_location_name",
            field=models.CharField(blank=True, max_length=200),
        ),
    ]
