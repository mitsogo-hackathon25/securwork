from django.db import migrations, models
from django.utils.text import slugify


DEFAULT_BRANDS = [
    "Payper",
    "James Ross Collection",
    "U-Power",
    "Isacco",
    "Kariban",
    "Spargo",
    "Valento",
    "Giblor's",
    "Sottozero",
    "Carine",
    "Promit",
]


def seed_brands(apps, schema_editor):
    Brand = apps.get_model("store", "Brand")
    Product = apps.get_model("store", "Product")
    names = set(DEFAULT_BRANDS)
    names.update(Product.objects.exclude(brand="").values_list("brand", flat=True))
    used_slugs = set()
    for i, name in enumerate(sorted(names, key=str.casefold)):
        if not name:
            continue
        if Brand.objects.filter(name__iexact=name).exists():
            continue
        base_slug = slugify(name)[:110] or f"brand-{i}"
        slug = base_slug
        counter = 1
        while slug in used_slugs or Brand.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        used_slugs.add(slug)
        Brand.objects.create(name=name, slug=slug, sort_order=i)


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0003_product_brand"),
    ]

    operations = [
        migrations.CreateModel(
            name="Brand",
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
        migrations.RunPython(seed_brands, migrations.RunPython.noop),
    ]
