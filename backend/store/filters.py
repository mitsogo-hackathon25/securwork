from rest_framework.filters import BaseFilterBackend

from .search import filter_products_by_search


class BilingualProductSearchFilter(BaseFilterBackend):
    """Search products in Italian and English (and SKU/brand), ignoring UI language."""

    search_param = "search"

    def filter_queryset(self, request, queryset, view):
        term = request.query_params.get(self.search_param, "")
        return filter_products_by_search(queryset, term)
