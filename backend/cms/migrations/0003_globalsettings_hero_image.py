from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cms", "0002_globalsettings"),
    ]

    operations = [
        migrations.AddField(
            model_name="globalsettings",
            name="hero_image",
            field=models.ImageField(blank=True, null=True, upload_to="home/"),
        ),
    ]
