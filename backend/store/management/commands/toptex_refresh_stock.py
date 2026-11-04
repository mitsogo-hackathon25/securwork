"""Pull TopTex inventory and update ProductVariant.stock_quantity for existing products."""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db.models import Prefetch

from store.models import Product, ProductVariant
from store.toptex_client import TopTexAPIError, TopTexClient, TopTexConfigError
from store.toptex_import import build_stock_by_sku_from_inventory


class Command(BaseCommand):
    help = "Refresh variant stock from TopTex inventory API (by product Codice Padre / sku)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--catalog-ref",
            dest="catalog_ref",
            default="",
            help="Only refresh this Codice Padre (product sku).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print counts without writing to the database.",
        )

    def handle(self, *args, **options):
        catalog_ref = (options.get("catalog_ref") or "").strip()
        dry_run = bool(options.get("dry_run"))

        try:
            client = TopTexClient()
            client.ensure_configured()
            client.authenticate()
        except (TopTexConfigError, TopTexAPIError) as exc:
            self.stderr.write(self.style.ERROR(str(exc)))
            return

        qs = Product.objects.prefetch_related(
            Prefetch("variants", queryset=ProductVariant.objects.all()),
        ).order_by("sku")
        if catalog_ref:
            qs = qs.filter(sku__iexact=catalog_ref)

        updated_variants = 0
        products_checked = 0
        for product in qs.iterator():
            ref = (product.sku or "").strip()
            if not ref:
                continue
            products_checked += 1
            stock_by_sku = build_stock_by_sku_from_inventory(client, [ref])
            if not stock_by_sku:
                self.stdout.write(f"{ref}: no inventory rows parsed")
                continue
            for variant in product.variants.all():
                qty = stock_by_sku.get((variant.sku or "").strip().lower())
                if qty is None:
                    continue
                if variant.stock_quantity != qty:
                    if not dry_run:
                        variant.stock_quantity = qty
                        variant.save(update_fields=["stock_quantity"])
                    updated_variants += 1

        suffix = " (dry run)" if dry_run else ""
        self.stdout.write(
            self.style.SUCCESS(
                f"Checked {products_checked} product(s), updated {updated_variants} variant(s){suffix}.",
            ),
        )
