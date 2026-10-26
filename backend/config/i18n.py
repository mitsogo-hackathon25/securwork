"""API language selection (matches storefront ?lang= query param)."""

SUPPORTED_LANGS = frozenset({"it", "en"})


def normalize_lang(value: str | None, default: str = "it") -> str:
    if not value:
        return default
    code = str(value).strip().lower()[:2]
    return code if code in SUPPORTED_LANGS else default


def request_language(request, default: str = "it") -> str:
    raw = request.GET.get("lang")
    if not raw and hasattr(request, "POST"):
        raw = request.POST.get("lang")
    return normalize_lang(raw, default=default)
