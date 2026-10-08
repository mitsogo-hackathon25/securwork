"""Product search across all languages (not limited to the storefront UI language)."""
from django.db.models import Q, QuerySet

from .models import Product


def filter_products_by_search(queryset: QuerySet[Product], term: str) -> QuerySet[Product]:
    words = [part.strip() for part in (term or "").split() if part.strip()]
    if not words:
        return queryset

    for word in words:
        queryset = queryset.filter(
            Q(translations__name__icontains=word)
            | Q(translations__short_description__icontains=word)
            | Q(translations__description__icontains=word)
            | Q(sku__icontains=word)
            | Q(slug__icontains=word)
            | Q(brand__icontains=word)
            | Q(variants__sku__icontains=word)
        )
    return queryset.distinct()
