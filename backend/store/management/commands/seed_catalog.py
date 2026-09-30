"""
Seed ~50 demo products with placeholder images across all categories.
Usage: python manage.py seed_catalog [--clear]
"""
import io
from decimal import Decimal
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from PIL import Image, ImageDraw, ImageFont

from orders.models import Coupon
from store.models import Category, Product, ProductImage, ProductVariant

COLORS = [
    (26, 43, 74), (45, 74, 122), (55, 65, 81), (30, 58, 95),
    (232, 93, 4), (75, 85, 99), (31, 41, 55), (15, 26, 46),
]

PRODUCTS = [
    # Workwear — T-shirt (4)
    {"cat": "t-shirt", "sku": "SW-TS-001", "slug": "demo-tshirt-operativa-blu", "it": "T-shirt operativa blu", "en": "Blue work t-shirt", "price": "14.90", "featured": True, "new": True},
    {"cat": "t-shirt", "sku": "SW-TS-002", "slug": "demo-tshirt-operativa-grigia", "it": "T-shirt operativa grigia", "en": "Grey work t-shirt", "price": "14.90"},
    {"cat": "t-shirt", "sku": "SW-TS-003", "slug": "demo-tshirt-maniche-lunghe", "it": "T-shirt maniche lunghe", "en": "Long sleeve work t-shirt", "price": "18.50", "bestseller": True},
    {"cat": "t-shirt", "sku": "SW-TS-004", "slug": "demo-tshirt-alta-visibilita", "it": "T-shirt alta visibilità", "en": "High-visibility t-shirt", "price": "22.00", "featured": True},
    # Polo (4)
    {"cat": "polo", "sku": "SW-PL-001", "slug": "demo-polo-classica-navy", "it": "Polo classica navy", "en": "Classic navy polo", "price": "19.90", "featured": True},
    {"cat": "polo", "sku": "SW-PL-002", "slug": "demo-polo-bicolore", "it": "Polo bicolore", "en": "Two-tone polo shirt", "price": "21.50"},
    {"cat": "polo", "sku": "SW-PL-003", "slug": "demo-polo-manica-lunga", "it": "Polo manica lunga", "en": "Long sleeve polo", "price": "24.90", "new": True},
    {"cat": "polo", "sku": "SW-PL-004", "slug": "demo-polo-fluorescente", "it": "Polo fluorescente", "en": "Fluorescent polo", "price": "26.00"},
    # Pantaloni da lavoro (4)
    {"cat": "pantaloni-da-lavoro", "sku": "SW-PT-001", "slug": "demo-pantalone-multitasche", "it": "Pantalone multitasche", "en": "Multi-pocket work trousers", "price": "39.90", "bestseller": True, "featured": True},
    {"cat": "pantaloni-da-lavoro", "sku": "SW-PT-002", "slug": "demo-pantalone-elastico", "it": "Pantalone elastico", "en": "Elastic waist work trousers", "price": "35.00"},
    {"cat": "pantaloni-da-lavoro", "sku": "SW-PT-003", "slug": "demo-pantalone-canvas", "it": "Pantalone canvas rinforzato", "en": "Reinforced canvas trousers", "price": "45.00"},
    {"cat": "pantaloni-da-lavoro", "sku": "SW-PT-004", "slug": "demo-pantalone-estivo", "it": "Pantalone estivo leggero", "en": "Light summer work trousers", "price": "32.00", "new": True},
    # Scarpe (3)
    {"cat": "scarpe-da-lavoro", "sku": "SW-SC-001", "slug": "demo-scarpa-antinfortunistica-s3", "it": "Scarpa antinfortunistica S3", "en": "S3 safety shoes", "price": "59.90", "featured": True},
    {"cat": "scarpe-da-lavoro", "sku": "SW-SC-002", "slug": "demo-scarpa-antiscivolo", "it": "Scarpa antiscivolo", "en": "Non-slip safety shoes", "price": "49.90", "bestseller": True},
    {"cat": "scarpe-da-lavoro", "sku": "SW-SC-003", "slug": "demo-stivale-impermeabile", "it": "Stivale impermeabile", "en": "Waterproof safety boots", "price": "74.90"},
    # Giacche (3)
    {"cat": "giacche", "sku": "SW-GC-001", "slug": "demo-giacca-softshell", "it": "Giacca softshell", "en": "Softshell jacket", "price": "54.90", "featured": True},
    {"cat": "giacche", "sku": "SW-GC-002", "slug": "demo-giacca-impermeabile", "it": "Giacca impermeabile", "en": "Waterproof jacket", "price": "64.00", "new": True},
    {"cat": "giacche", "sku": "SW-GC-003", "slug": "demo-giacca-invernale", "it": "Giacca invernale imbottita", "en": "Padded winter jacket", "price": "89.00", "bestseller": True},
    # Gilet (2)
    {"cat": "gilet", "sku": "SW-GL-001", "slug": "demo-gilet-multitasche", "it": "Gilet multitasche", "en": "Multi-pocket body warmer", "price": "29.90"},
    {"cat": "gilet", "sku": "SW-GL-002", "slug": "demo-gilet-alta-visibilita", "it": "Gilet alta visibilità", "en": "High-vis body warmer", "price": "18.50", "featured": True},
    # Felpe (3)
    {"cat": "felpe", "sku": "SW-FL-001", "slug": "demo-felpa-cappuccio", "it": "Felpa con cappuccio", "en": "Hooded sweatshirt", "price": "34.90", "new": True},
    {"cat": "felpe", "sku": "SW-FL-002", "slug": "demo-felpa-zip", "it": "Felpa con zip", "en": "Zip-up hoodie", "price": "38.00"},
    {"cat": "felpe", "sku": "SW-FL-003", "slug": "demo-felpa-pile", "it": "Felpa pile", "en": "Fleece sweatshirt", "price": "42.00"},
    # Maglioni (2)
    {"cat": "maglioni", "sku": "SW-MG-001", "slug": "demo-maglione-lana", "it": "Maglione lana", "en": "Wool sweater", "price": "44.90"},
    {"cat": "maglioni", "sku": "SW-MG-002", "slug": "demo-maglione-pile", "it": "Maglione pile", "en": "Fleece sweater", "price": "39.00"},
    # Guanti (3)
    {"cat": "guanti", "sku": "SW-GU-001", "slug": "demo-guanti-anticorte", "it": "Guanti anticorte", "en": "Cut-resistant gloves", "price": "12.90"},
    {"cat": "guanti", "sku": "SW-GU-002", "slug": "demo-guanti-nitrile", "it": "Guanti nitrile", "en": "Nitrile gloves (pack)", "price": "8.50", "bestseller": True},
    {"cat": "guanti", "sku": "SW-GU-003", "slug": "demo-guanti-invernali", "it": "Guanti invernali", "en": "Winter work gloves", "price": "15.00"},
    # Camicie (3)
    {"cat": "camicie", "sku": "SW-CM-001", "slug": "demo-camicia-operativa", "it": "Camicia operativa", "en": "Work shirt", "price": "27.90"},
    {"cat": "camicie", "sku": "SW-CM-002", "slug": "demo-camicia-flanella", "it": "Camicia flanella", "en": "Flannel work shirt", "price": "32.00", "new": True},
    {"cat": "camicie", "sku": "SW-CM-003", "slug": "demo-camicia-oxford", "it": "Camicia oxford", "en": "Oxford work shirt", "price": "29.50"},
    # Salopette (2)
    {"cat": "salopette", "sku": "SW-SL-001", "slug": "demo-salopette-canvas", "it": "Salopette canvas", "en": "Canvas bib overalls", "price": "52.00"},
    {"cat": "salopette", "sku": "SW-SL-002", "slug": "demo-salopette-invernale", "it": "Salopette invernale", "en": "Winter bib overalls", "price": "68.00", "featured": True},
    # Camici (2)
    {"cat": "camici", "sku": "SW-CA-001", "slug": "demo-camice-da-lavoro", "it": "Camice da lavoro", "en": "Work coat", "price": "36.00"},
    {"cat": "camici", "sku": "SW-CA-002", "slug": "demo-camice-pile", "it": "Camice pile", "en": "Fleece work coat", "price": "48.00"},
    # Professional — Grembiuli (3)
    {"cat": "grembiuli", "sku": "SW-GR-001", "slug": "demo-grembiule-cucina", "it": "Grembiule cucina", "en": "Kitchen apron", "price": "16.90", "featured": True},
    {"cat": "grembiuli", "sku": "SW-GR-002", "slug": "demo-grembiule-pettorina", "it": "Grembiule con pettorina", "en": "Bib apron", "price": "19.50"},
    {"cat": "grembiuli", "sku": "SW-GR-003", "slug": "demo-grembiule-porta-utensili", "it": "Grembiule porta utensili", "en": "Tool-pocket apron", "price": "22.00"},
    # Pantaloni professionali (3)
    {"cat": "pantaloni-professionali", "sku": "SW-PP-001", "slug": "demo-pantalone-chef", "it": "Pantalone chef", "en": "Chef trousers", "price": "34.90"},
    {"cat": "pantaloni-professionali", "sku": "SW-PP-002", "slug": "demo-pantalone-servizio", "it": "Pantalone servizio", "en": "Service trousers", "price": "29.90", "new": True},
    {"cat": "pantaloni-professionali", "sku": "SW-PP-003", "slug": "demo-pantalone-bar", "it": "Pantalone bar", "en": "Bar staff trousers", "price": "31.00"},
    # Sanitario (3)
    {"cat": "abbigliamento-sanitario", "sku": "SW-SA-001", "slug": "demo-casacca-sanitaria", "it": "Casacca sanitaria", "en": "Healthcare tunic", "price": "28.00", "featured": True},
    {"cat": "abbigliamento-sanitario", "sku": "SW-SA-002", "slug": "demo-pantalone-sanitario", "it": "Pantalone sanitario", "en": "Healthcare trousers", "price": "24.90"},
    {"cat": "abbigliamento-sanitario", "sku": "SW-SA-003", "slug": "demo-camice-sanitario", "it": "Camice sanitario", "en": "Healthcare coat", "price": "32.00", "bestseller": True},
    # Alimentare (3)
    {"cat": "abbigliamento-alimentare", "sku": "SW-AL-001", "slug": "demo-cappello-cuoco", "it": "Cappello cuoco", "en": "Chef hat", "price": "9.90"},
    {"cat": "abbigliamento-alimentare", "sku": "SW-AL-002", "slug": "demo-giacca-cuoco", "it": "Giacca cuoco", "en": "Chef jacket", "price": "42.00", "featured": True},
    {"cat": "abbigliamento-alimentare", "sku": "SW-AL-003", "slug": "demo-cuffia-alimentare", "it": "Cuffia alimentare", "en": "Food industry hairnet (pack)", "price": "6.50"},
    # Divise (3)
    {"cat": "divise-professionali", "sku": "SW-DV-001", "slug": "demo-divisa-completa", "it": "Divisa completa", "en": "Complete uniform set", "price": "79.00", "featured": True},
    {"cat": "divise-professionali", "sku": "SW-DV-002", "slug": "demo-giacca-divisa", "it": "Giacca divisa", "en": "Uniform jacket", "price": "45.00", "new": True},
    {"cat": "divise-professionali", "sku": "SW-DV-003", "slug": "demo-polo-divisa", "it": "Polo divisa", "en": "Uniform polo", "price": "22.00", "bestseller": True},
]


def generate_placeholder_image(sku: str, color: tuple) -> ContentFile:
    img = Image.new("RGB", (800, 1000), color)
    draw = ImageDraw.Draw(img)
    # Subtle diagonal lines
    for i in range(0, 1000, 40):
        draw.line([(0, i), (800, i + 200)], fill=(255, 255, 255, 30), width=1)
    # Product label
    text = f"[DEMO]\n{sku}"
    try:
        font = ImageFont.truetype("arial.ttf", 36)
    except OSError:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((800 - tw) / 2, (1000 - th) / 2), text, fill=(255, 255, 255), font=font)
    draw.rectangle([40, 40, 760, 960], outline=(255, 255, 255), width=2)
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=85)
    buffer.seek(0)
    return ContentFile(buffer.read(), name=f"{sku.lower()}.jpg")


class Command(BaseCommand):
    help = "Seed 50 demo products with placeholder images"

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true", help="Remove existing DEMO/SW- products first")

    def handle(self, *args, **options):
        if options["clear"]:
            self.stdout.write("Clearing existing catalog products...")
            Product.objects.filter(sku__startswith="SW-").delete()
            Product.objects.filter(sku__startswith="DEMO-").delete()

        categories = {c.slug: c for c in Category.objects.filter(parent__isnull=False)}
        if not categories:
            self.stdout.write(self.style.ERROR("No categories found. Run seed_data first."))
            return

        sizes = ["S", "M", "L", "XL", "XXL"]
        colors = ["Nero", "Blu", "Grigio"]
        created_count = 0

        for i, pdata in enumerate(PRODUCTS):
            cat = categories.get(pdata["cat"])
            if not cat:
                self.stdout.write(self.style.WARNING(f"Category {pdata['cat']} not found, skipping {pdata['sku']}"))
                continue

            product, was_created = Product.objects.get_or_create(
                sku=pdata["sku"],
                defaults={
                    "slug": pdata["slug"],
                    "is_featured": pdata.get("featured", False),
                    "is_new_arrival": pdata.get("new", False),
                    "is_bestseller": pdata.get("bestseller", False),
                },
            )
            product.slug = pdata["slug"]
            product.is_featured = pdata.get("featured", False)
            product.is_new_arrival = pdata.get("new", False)
            product.is_bestseller = pdata.get("bestseller", False)
            product.is_active = True
            product.save()
            product.categories.set([cat])

            desc_it = (
                f"<p>[DEMO] {pdata['it']} — prodotto dimostrativo per il catalogo SecurWork. "
                "Sostituire con descrizione reale. Nessuna affermazione commerciale.</p>"
            )
            desc_en = (
                f"<p>[DEMO] {pdata['en']} — demo catalogue product for SecurWork. "
                "Replace with real description. No commercial claims.</p>"
            )
            product.set_current_language("it")
            product.name = f"[DEMO] {pdata['it']}"
            product.short_description = "Prodotto dimostrativo — dati da sostituire."
            product.description = desc_it
            product.meta_title = pdata["it"]
            product.save()
            product.set_current_language("en")
            product.name = f"[DEMO] {pdata['en']}"
            product.short_description = "Demo product — replace with real data."
            product.description = desc_en
            product.meta_title = pdata["en"]
            product.save()

            base_price = Decimal(pdata["price"])
            sale = None
            if i % 7 == 0:
                sale = (base_price * Decimal("0.85")).quantize(Decimal("0.01"))

            for size in sizes[:4]:
                for color in colors[:2]:
                    vsku = f"{pdata['sku']}-{size}-{color[:3].upper()}"
                    ProductVariant.objects.update_or_create(
                        sku=vsku,
                        defaults={
                            "product": product,
                            "size": size,
                            "color": color,
                            "price": base_price,
                            "sale_price": sale,
                            "stock_quantity": 15 + (i % 10),
                            "is_active": True,
                        },
                    )

            if not product.images.exists():
                img_file = generate_placeholder_image(pdata["sku"], COLORS[i % len(COLORS)])
                pi = ProductImage(product=product, is_primary=True, alt_text=pdata["it"])
                pi.image.save(f"{pdata['sku'].lower()}.jpg", img_file, save=True)

            created_count += 1

        Coupon.objects.get_or_create(
            code="BIENVENUTO10",
            defaults={
                "discount_percent": Decimal("10.00"),
                "min_order_amount": Decimal("30.00"),
                "max_uses": 100,
                "is_active": True,
            },
        )

        self.stdout.write(self.style.SUCCESS(f"Catalog seeded: {created_count} products, coupon BIENVENUTO10 created."))
