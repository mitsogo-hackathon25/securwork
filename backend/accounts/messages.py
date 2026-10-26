"""Bilingual API validation copy (storefront lang=it|en)."""

from config.i18n import normalize_lang

_MESSAGES: dict[str, dict[str, str]] = {
    "password_mismatch": {
        "it": "Le password non coincidono.",
        "en": "Passwords do not match.",
    },
    "username_taken": {
        "it": "Questo nome utente è già in uso.",
        "en": "This username is already taken.",
    },
    "email_taken": {
        "it": "Questa email è già registrata.",
        "en": "This email is already registered.",
    },
    "email_invalid": {
        "it": "Inserisci un indirizzo email valido.",
        "en": "Enter a valid email address.",
    },
}


def api_message(key: str, lang: str | None) -> str:
    code = normalize_lang(lang)
    table = _MESSAGES.get(key, {})
    return table.get(code) or table.get("it") or key


def lang_from_serializer_context(context: dict) -> str:
    request = context.get("request")
    if request is not None:
        return normalize_lang(getattr(request, "LANGUAGE_CODE", None))
    return normalize_lang(context.get("lang"))
