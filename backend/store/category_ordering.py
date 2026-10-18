"""Alphabetical category ordering (locale-aware name, slug fallback)."""

from __future__ import annotations

from typing import Iterable

from .models import Category


def category_display_name(category: Category, lang: str = "it") -> str:
    return (
        category.safe_translation_getter("name", language_code=lang, any_language=True)
        or category.slug
    )


def category_sort_key(category: Category, lang: str = "it") -> str:
    return category_display_name(category, lang).casefold()


def sort_categories(categories: Iterable[Category], lang: str = "it") -> list[Category]:
    return sorted(categories, key=lambda c: category_sort_key(c, lang))
