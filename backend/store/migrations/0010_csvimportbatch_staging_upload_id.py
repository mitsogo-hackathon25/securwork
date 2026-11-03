from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0009_csv_import_batch"),
    ]

    operations = [
        migrations.AddField(
            model_name="csvimportbatch",
            name="staging_upload_id",
            field=models.CharField(blank=True, max_length=36),
        ),
    ]
