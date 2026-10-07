from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0005_color"),
    ]

    operations = [
        migrations.AddField(
            model_name="productimage",
            name="external_url",
            field=models.URLField(blank=True, max_length=500),
        ),
        migrations.AlterField(
            model_name="productimage",
            name="image",
            field=models.ImageField(blank=True, null=True, upload_to="products/"),
        ),
    ]
