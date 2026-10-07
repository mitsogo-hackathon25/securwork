from django.db import migrations, models
from django.utils.text import slugify

DEFAULT_COLORS = [
    "Nero",
    "Blu",
    "Grigio",
    "Bianco",
    "Rosso",
    "Verde",
    "Giallo",
    "Arancione",
    "Beige",
    "Navy",
]


def seed_colors(apps, schema_editor):
    Color = apps.get_model("store", "Color")
    ProductVariant = apps.get_model("store", "ProductVariant")
    names = set(DEFAULT_COLORS)
    names.update(ProductVariant.objects.exclude(color="").values_list("color", flat=True))
    used_slugs = set()
    for i, name in enumerate(sorted(names, key=str.casefold)):
        if not name:
            continue
        if Color.objects.filter(name__iexact=name).exists():
            continue
        base_slug = slugify(name)[:110] or f"color-{i}"
        slug = base_slug
        counter = 1
        while slug in used_slugs or Color.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        used_slugs.add(slug)
        Color.objects.create(name=name, slug=slug, sort_order=i)


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0004_brand"),
    ]

    operations = [
        migrations.CreateModel(
            name="Color",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100, unique=True)),
                ("slug", models.SlugField(blank=True, max_length=120, unique=True)),
                ("is_active", models.BooleanField(default=True)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["sort_order", "name"],
            },
        ),
        migrations.RunPython(seed_colors, migrations.RunPython.noop),
    ]
