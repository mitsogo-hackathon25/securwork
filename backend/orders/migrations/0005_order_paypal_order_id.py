# Generated manually for PayPal integration

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0004_customization_methods"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="paypal_order_id",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AlterField(
            model_name="order",
            name="payment_method",
            field=models.CharField(
                choices=[
                    ("stripe", "Carta (Stripe)"),
                    ("paypal", "PayPal"),
                    ("bank_transfer", "Bonifico bancario"),
                    ("manual", "Manuale"),
                ],
                default="stripe",
                max_length=20,
            ),
        ),
    ]
