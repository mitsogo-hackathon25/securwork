"""
Seed ~50 demo products with placeholder images across all categories.
Usage: python manage.py seed_catalog [--clear] [--images-only]
"""
from decimal import Decimal

from django.core.management.base import BaseCommand

from orders.models import Coupon
from store.constants import CLOTHING_SIZES, PRODUCT_COLORS
from store.image_utils import generate_category_image, generate_product_image, get_category_image, get_product_image
from store.models import Category, Product, ProductImage, ProductVariant

CUSTOMIZABLE_CATEGORIES = {
    "t-shirt", "polo", "felpe", "camicie", "giacche", "gilet", "maglioni",
    "salopette", "camici", "cappelli", "pantaloncini-bermuda",
    "grembiuli", "linea-chef", "abbigliamento-sanitario", "hotel-ristorante-caffe",
    "parrucchiere", "abbigliamento-alimentare", "divise-professionali", "taglia-unica",
    "imprese-di-pulizie",
}

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
    # Pantaloncini e Bermuda (2)
    {"cat": "pantaloncini-bermuda", "sku": "SW-PB-001", "slug": "demo-pantaloncino-operativo", "it": "Pantaloncino operativo", "en": "Work shorts", "price": "24.90", "new": True},
    {"cat": "pantaloncini-bermuda", "sku": "SW-PB-002", "slug": "demo-bermuda-multitasche", "it": "Bermuda multitasche", "en": "Multi-pocket bermuda shorts", "price": "28.00"},
    # Scarpe (3) — also in Abbigliamento professionale via also_cat
    {"cat": "scarpe-da-lavoro", "also_cat": "scarpe-professionali", "brand": "U-Power", "sku": "SW-SC-001", "slug": "demo-scarpa-antinfortunistica-s3", "it": "Scarpa antinfortunistica S3", "en": "S3 safety shoes", "price": "59.90", "featured": True},
    {"cat": "scarpe-da-lavoro", "also_cat": "scarpe-professionali", "brand": "Valento", "sku": "SW-SC-002", "slug": "demo-scarpa-antiscivolo", "it": "Scarpa antiscivolo", "en": "Non-slip safety shoes", "price": "49.90", "bestseller": True},
    {"cat": "scarpe-da-lavoro", "also_cat": "scarpe-professionali", "brand": "U-Power", "sku": "SW-SC-003", "slug": "demo-stivale-impermeabile", "it": "Stivale impermeabile", "en": "Waterproof safety boots", "price": "74.90"},
    # Cappelli (2)
    {"cat": "cappelli", "brand": "Promit", "sku": "SW-CP-001", "slug": "demo-cappello-estate", "it": "Cappello operativo estivo", "en": "Summer work cap", "price": "8.90", "new": True},
    {"cat": "cappelli", "brand": "Valento", "sku": "SW-CP-002", "slug": "demo-berretto-invernale", "it": "Berretto invernale", "en": "Winter work beanie", "price": "7.50"},
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
    # Accessori Antinfortunistica (2)
    {"cat": "accessori-antinfortunistica", "sku": "SW-AA-001", "slug": "demo-imbracatura-sicurezza", "it": "Imbracatura di sicurezza", "en": "Safety harness", "price": "45.00", "featured": True},
    {"cat": "accessori-antinfortunistica", "sku": "SW-AA-002", "slug": "demo-cordino-anticaduta", "it": "Cordino anticaduta", "en": "Fall arrest lanyard", "price": "32.00"},
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
    # Imprese di Pulizie (2)
    {"cat": "imprese-di-pulizie", "brand": "Kariban", "sku": "SW-IP-001", "slug": "demo-tunica-pulizie", "it": "Tunica imprese di pulizie", "en": "Cleaning company tunic", "price": "26.00", "featured": True},
    {"cat": "imprese-di-pulizie", "brand": "Spargo", "sku": "SW-IP-002", "slug": "demo-pantalone-pulizie", "it": "Pantalone imprese di pulizie", "en": "Cleaning company trousers", "price": "29.00"},
    # Sanitario (3)
    {"cat": "abbigliamento-sanitario", "sku": "SW-SA-001", "slug": "demo-casacca-sanitaria", "it": "Casacca sanitaria", "en": "Healthcare tunic", "price": "28.00", "featured": True},
    {"cat": "abbigliamento-sanitario", "sku": "SW-SA-002", "slug": "demo-pantalone-sanitario", "it": "Pantalone sanitario", "en": "Healthcare trousers", "price": "24.90"},
    {"cat": "abbigliamento-sanitario", "sku": "SW-SA-003", "slug": "demo-camice-sanitario", "it": "Camice sanitario", "en": "Healthcare coat", "price": "32.00", "bestseller": True},
    # Linea Chef (3)
    {"cat": "linea-chef", "brand": "ISACCO", "sku": "SW-CH-001", "slug": "demo-giacca-chef-classica", "it": "Giacca chef classica", "en": "Classic chef jacket", "price": "44.00", "featured": True},
    {"cat": "linea-chef", "brand": "ISACCO", "sku": "SW-CH-002", "slug": "demo-pantalone-chef-linea", "it": "Pantalone chef", "en": "Chef trousers", "price": "36.00", "new": True},
    {"cat": "linea-chef", "brand": "Payper", "sku": "SW-CH-003", "slug": "demo-cappello-chef", "it": "Cappello chef", "en": "Chef hat", "price": "9.90"},
    # Taglia Unica (2)
    {"cat": "taglia-unica", "brand": "James Ross Collection", "sku": "SW-TU-001", "slug": "demo-casacca-taglia-unica", "it": "Casacca taglia unica", "en": "One-size tunic", "price": "26.00"},
    {"cat": "taglia-unica", "brand": "James Ross Collection", "sku": "SW-TU-002", "slug": "demo-grembiule-taglia-unica", "it": "Grembiule taglia unica", "en": "One-size apron", "price": "18.00", "featured": True},
    # Hotel, Ristorante e Caffè (3)
    {"cat": "hotel-ristorante-caffe", "brand": "ISACCO", "sku": "SW-HR-001", "slug": "demo-camicia-servizio", "it": "Camicia servizio", "en": "Service shirt", "price": "32.00", "featured": True},
    {"cat": "hotel-ristorante-caffe", "brand": "Payper", "sku": "SW-HR-002", "slug": "demo-gilet-cameriere", "it": "Gilet cameriere", "en": "Waiter waistcoat", "price": "38.00"},
    {"cat": "hotel-ristorante-caffe", "brand": "Promit", "sku": "SW-HR-003", "slug": "demo-polo-bar", "it": "Polo bar", "en": "Bar staff polo", "price": "24.00", "bestseller": True},
    # Parrucchiere (2)
    {"cat": "parrucchiere", "brand": "Valento", "sku": "SW-PR-001", "slug": "demo-grembiule-parrucchiere", "it": "Grembiule parrucchiere", "en": "Hairdresser apron", "price": "22.00", "featured": True},
    {"cat": "parrucchiere", "brand": "Sottozero", "sku": "SW-PR-002", "slug": "demo-casacca-parrucchiere", "it": "Casacca parrucchiere", "en": "Hairdresser tunic", "price": "28.00"},
    # Alimentare (3)
    {"cat": "abbigliamento-alimentare", "brand": "ISACCO", "sku": "SW-AL-001", "slug": "demo-cappello-cuoco", "it": "Cappello cuoco", "en": "Chef hat", "price": "9.90"},
    {"cat": "abbigliamento-alimentare", "brand": "ISACCO", "sku": "SW-AL-002", "slug": "demo-giacca-cuoco", "it": "Giacca cuoco", "en": "Chef jacket", "price": "42.00", "featured": True},
    {"cat": "abbigliamento-alimentare", "brand": "Payper", "sku": "SW-AL-003", "slug": "demo-cuffia-alimentare", "it": "Cuffia alimentare", "en": "Food industry hairnet (pack)", "price": "6.50"},
    # Divise (3)
    {"cat": "divise-professionali", "sku": "SW-DV-001", "slug": "demo-divisa-completa", "it": "Divisa completa", "en": "Complete uniform set", "price": "79.00", "featured": True},
    {"cat": "divise-professionali", "sku": "SW-DV-002", "slug": "demo-giacca-divisa", "it": "Giacca divisa", "en": "Uniform jacket", "price": "45.00", "new": True},
    {"cat": "divise-professionali", "sku": "SW-DV-003", "slug": "demo-polo-divisa", "it": "Polo divisa", "en": "Uniform polo", "price": "22.00", "bestseller": True},
]


def seed_category_images(stdout, style, force=False):
    count = 0
    for cat in Category.objects.filter(is_active=True):
        if cat.image and not force:
            continue
        img_file = get_category_image(cat.slug, cat.section)
        cat.image.save(f"cat-{cat.slug}.jpg", img_file, save=True)
        count += 1
    stdout.write(style.SUCCESS(f"Category images: {count} updated."))


def seed_product_images(stdout, style, force=False):
    count = 0
    for product in Product.objects.filter(is_active=True):
        if product.images.exists() and not force:
            continue
        if force:
            product.images.all().delete()
        name = product.safe_translation_getter("name", language_code="it", any_language=True) or product.sku
        label = name.replace("[DEMO] ", "")
        cat = product.categories.filter(parent__isnull=False).first() or product.categories.first()
        cat_slug = cat.slug if cat else None
        img_file = get_product_image(product.sku, cat_slug)
        pi = ProductImage(product=product, is_primary=True, alt_text=label)
        pi.image.save(f"{product.sku.lower()}.jpg", img_file, save=True)
        count += 1
    stdout.write(style.SUCCESS(f"Product images: {count} updated."))


class Command(BaseCommand):
    help = "Seed 50 demo products with placeholder images"

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true", help="Remove existing DEMO/SW- products first")
        parser.add_argument("--images-only", action="store_true", help="Only (re)generate category and product images")
        parser.add_argument("--force-images", action="store_true", help="Replace existing product images")

    def handle(self, *args, **options):
        if options["images_only"]:
            seed_category_images(self.stdout, self.style, force=options["force_images"])
            seed_product_images(self.stdout, self.style, force=options["force_images"])
            return

        if options["clear"]:
            self.stdout.write("Clearing existing catalog products...")
            Product.objects.filter(sku__startswith="SW-").delete()
            Product.objects.filter(sku__startswith="DEMO-").delete()

        categories = {c.slug: c for c in Category.objects.filter(parent__isnull=False)}
        if not categories:
            self.stdout.write(self.style.ERROR("No categories found. Run seed_data first."))
            return

        sizes = list(CLOTHING_SIZES)
        colors = list(PRODUCT_COLORS)
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
            product.brand = pdata.get("brand", "")
            product.is_featured = pdata.get("featured", False)
            product.is_new_arrival = pdata.get("new", False)
            product.is_bestseller = pdata.get("bestseller", False)
            product.is_active = True
            product.allows_customization = pdata["cat"] in CUSTOMIZABLE_CATEGORIES
            if product.allows_customization and product.customization_fee == Decimal("0.00"):
                product.customization_fee = Decimal("5.00")
            product.save()
            cats = [cat]
            also = pdata.get("also_cat")
            if also and also in categories:
                cats.append(categories[also])
            product.categories.set(cats)

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
                img_file = get_product_image(pdata["sku"], pdata["cat"])
                pi = ProductImage(product=product, is_primary=True, alt_text=pdata["it"])
                pi.image.save(f"{pdata['sku'].lower()}.jpg", img_file, save=True)

            created_count += 1

        seed_category_images(self.stdout, self.style, force=options.get("force_images", False))
        seed_product_images(self.stdout, self.style, force=options.get("force_images", False))

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
