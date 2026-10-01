import json
from decimal import Decimal
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from cms.content_seed import PAGE_CONTENT
from cms.models import FAQItem, Page
from store.image_utils import get_category_image, get_product_image
from store.models import Category, Product, ProductImage, ProductVariant

User = get_user_model()

CATEGORIES_PATH = Path(__file__).resolve().parents[3] / "fixtures" / "categories.json"

PAGE_TYPES = [
    ("about", "about"),
    ("contact", "contact"),
    ("shipping", "shipping"),
    ("returns", "returns"),
    ("privacy", "privacy"),
    ("cookies", "cookies"),
    ("terms", "terms"),
]

FAQ_SEED = [
    ("Come posso effettuare un ordine?", "How can I place an order?",
     "Sfoglia il catalogo, seleziona taglia e colore, aggiungi al carrello e procedi al checkout.",
     "Browse the catalogue, select size and colour, add to cart and proceed to checkout."),
    ("Quali metodi di pagamento accettate?", "What payment methods do you accept?",
     "Accettiamo carte di credito/debito tramite Stripe e bonifico bancario.",
     "We accept credit/debit cards via Stripe and bank transfer."),
    ("Quanto tempo richiede la spedizione?", "How long does shipping take?",
     "Gli ordini vengono spediti entro 1–3 giorni lavorativi. Consegna in 2–5 giorni per l'Italia continentale.",
     "Orders ship within 1–3 business days. Delivery in 2–5 days for mainland Italy."),
]


class Command(BaseCommand):
    help = "Seed categories, placeholder pages, FAQ, demo products, and admin user"

    def add_arguments(self, parser):
        parser.add_argument("--admin-password", default="SecurWork_Admin_2026!")

    def handle(self, *args, **options):
        self.stdout.write("Seeding categories...")
        self._seed_categories()
        self.stdout.write("Seeding category images...")
        self._seed_category_images()
        self.stdout.write("Seeding CMS pages...")
        self._seed_pages()
        self.stdout.write("Seeding FAQ...")
        self._seed_faq()
        self.stdout.write("Seeding demo products...")
        self._seed_demo_products()
        self.stdout.write("Creating admin user...")
        self._create_admin(options["admin_password"])
        self.stdout.write(self.style.SUCCESS("Seed complete."))

    def _seed_categories(self):
        if not CATEGORIES_PATH.exists():
            self.stdout.write(self.style.WARNING(f"Categories file not found: {CATEGORIES_PATH}"))
            return
        data = json.loads(CATEGORIES_PATH.read_text(encoding="utf-8"))
        section_map = {
            "abbigliamento-da-lavoro": Category.Section.WORKWEAR,
            "abbigliamento-professionale": Category.Section.PROFESSIONAL,
        }
        for cat_data in data["categories"]:
            parent, _ = Category.objects.get_or_create(
                slug=cat_data["slug"],
                defaults={"section": section_map.get(cat_data["slug"], Category.Section.WORKWEAR)},
            )
            parent.set_current_language("it")
            parent.name = cat_data["name_it"]
            parent.save()
            parent.set_current_language("en")
            parent.name = cat_data["name_en"]
            parent.save()

            for i, child in enumerate(cat_data.get("children", [])):
                sub, _ = Category.objects.get_or_create(
                    slug=child["slug"],
                    defaults={"parent": parent, "section": parent.section, "sort_order": i},
                )
                sub.parent = parent
                sub.section = parent.section
                sub.sort_order = i
                sub.set_current_language("it")
                sub.name = child["name_it"]
                sub.save()
                sub.set_current_language("en")
                sub.name = child["name_en"]
                sub.save()

    def _seed_category_images(self):
        for cat in Category.objects.filter(is_active=True):
            if cat.image:
                continue
            img_file = get_category_image(cat.slug, cat.section)
            cat.image.save(f"cat-{cat.slug}.jpg", img_file, save=True)

    def _seed_pages(self):
        for page_type, slug in PAGE_TYPES:
            content = PAGE_CONTENT.get(page_type, {})
            page, created = Page.objects.get_or_create(
                page_type=page_type,
                defaults={"slug": slug},
            )
            existing_it = page.safe_translation_getter("content", language_code="it", any_language=True) or ""
            if not created and "[PLACEHOLDER]" not in existing_it and "Bozza informativa" not in existing_it:
                continue
            page.set_current_language("it")
            page.title = content.get("title_it", page_type)
            page.content = content.get("content_it", "")
            page.meta_title = content.get("meta_it", content.get("title_it", page_type))
            page.save()
            page.set_current_language("en")
            page.title = content.get("title_en", page_type)
            page.content = content.get("content_en", "")
            page.meta_title = content.get("meta_en", content.get("title_en", page_type))
            page.save()

    def _seed_faq(self):
        for i, (q_it, q_en, a_it, a_en) in enumerate(FAQ_SEED):
            faq, _ = FAQItem.objects.get_or_create(sort_order=i)
            faq.set_current_language("it")
            faq.question = q_it
            faq.answer = a_it
            faq.save()
            faq.set_current_language("en")
            faq.question = q_en
            faq.answer = a_en
            faq.save()

    def _seed_demo_products(self):
        categories = list(Category.objects.filter(parent__isnull=False)[:10])
        if not categories:
            return
        sizes = ["S", "M", "L", "XL"]
        colors = ["Nero", "Blu", "Grigio"]
        for i in range(1, 11):
            sku = f"DEMO-{i:03d}"
            product, created = Product.objects.get_or_create(
                sku=sku,
                defaults={"slug": f"prodotto-demo-{i}", "is_featured": i <= 4, "is_new_arrival": i <= 3},
            )
            product.categories.set([categories[i % len(categories)]])
            product.set_current_language("it")
            product.name = f"[DEMO] Prodotto campione {i}"
            product.short_description = "Prodotto dimostrativo — sostituire con dati reali."
            product.description = "<p>[PLACEHOLDER] Descrizione prodotto dimostrativo. Nessuna affermazione commerciale reale.</p>"
            product.save()
            product.set_current_language("en")
            product.name = f"[DEMO] Sample product {i}"
            product.short_description = "Demo product — replace with real data."
            product.description = "<p>[PLACEHOLDER] Demo product description. No real commercial claims.</p>"
            product.save()

            base_price = Decimal("29.90") + Decimal(i * 5)
            for size in sizes[:3]:
                for color in colors[:2]:
                    variant_sku = f"{sku}-{size}-{color[:3].upper()}"
                    ProductVariant.objects.get_or_create(
                        sku=variant_sku,
                        defaults={
                            "product": product,
                            "size": size,
                            "color": color,
                            "price": base_price,
                            "stock_quantity": 10 + i,
                        },
                    )

            if not product.images.exists():
                label = f"Prodotto campione {i}"
                cat = product.categories.filter(parent__isnull=False).first()
                img_file = get_product_image(sku, cat.slug if cat else None)
                pi = ProductImage(product=product, is_primary=True, alt_text=label)
                pi.image.save(f"{sku.lower()}.jpg", img_file, save=True)

    def _create_admin(self, password):
        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser(
                username="admin",
                email="admin@securwork.it",
                password=password,
            )
            self.stdout.write(self.style.SUCCESS(f"Admin created: admin / {password}"))
        else:
            self.stdout.write("Admin user already exists.")
