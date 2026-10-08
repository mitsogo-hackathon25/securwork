from decimal import Decimal

from django.db import migrations


def forwards(apps, schema_editor):
    Product = apps.get_model("store", "Product")
    for product in Product.objects.filter(allows_customization=True):
        if not any([
            product.embroidery_chest_enabled,
            product.embroidery_large_enabled,
            product.dtf_chest_enabled,
            product.dtf_large_enabled,
        ]):
            product.embroidery_chest_enabled = True
            product.embroidery_chest_fee = product.customization_fee or Decimal("0.00")
            product.save(update_fields=["embroidery_chest_enabled", "embroidery_chest_fee"])


def backwards(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("store", "0007_customization_methods"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
