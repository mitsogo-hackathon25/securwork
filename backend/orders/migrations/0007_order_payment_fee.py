from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0006_orderitem_variant_nullable"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="payment_fee",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0.00"),
                help_text="Payment processing fee charged to the customer (e.g. PayPal).",
                max_digits=10,
            ),
        ),
    ]
