from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0005_order_paypal_order_id"),
        ("store", "0008_migrate_customization_methods"),
    ]

    operations = [
        migrations.AlterField(
            model_name="orderitem",
            name="variant",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="store.productvariant",
            ),
        ),
    ]
