from django.db import migrations, models


def forwards_set_visibility(apps, schema_editor):
    Category = apps.get_model("store", "Category")
    for cat in Category.objects.all():
        sec = getattr(cat, "section", None) or "workwear"
        if sec == "professional":
            cat.visible_in_workwear = False
            cat.visible_in_professional = True
        else:
            cat.visible_in_workwear = True
            cat.visible_in_professional = False
        cat.save(update_fields=["visible_in_workwear", "visible_in_professional"])


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0010_csvimportbatch_staging_upload_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="category",
            name="visible_in_workwear",
            field=models.BooleanField(
                default=True,
                help_text="If true, this category appears when browsing the Workwear section.",
            ),
        ),
        migrations.AddField(
            model_name="category",
            name="visible_in_professional",
            field=models.BooleanField(
                default=False,
                help_text="If true, this category appears when browsing the Professional section.",
            ),
        ),
        migrations.RunPython(forwards_set_visibility, migrations.RunPython.noop),
    ]
