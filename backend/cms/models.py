import re

from django.core.validators import validate_email
from django.db import models
from parler.models import TranslatableModel, TranslatedFields


def parse_email_list(raw: str) -> list[str]:
    if not raw:
        return []
    parts = re.split(r"[,;\n]+", raw)
    emails: list[str] = []
    seen: set[str] = set()
    for part in parts:
        email = part.strip()
        if not email:
            continue
        validate_email(email)
        key = email.lower()
        if key not in seen:
            seen.add(key)
            emails.append(email)
    return emails


class GlobalSettings(models.Model):
    """One row (pk=1) for store-wide admin options."""

    order_notification_emails = models.TextField(
        blank=True,
        help_text="Comma- or line-separated addresses for new-order alerts only.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Global settings"
        verbose_name_plural = "Global settings"

    def __str__(self):
        return "Global settings"

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def recipient_list(self) -> list[str]:
        return parse_email_list(self.order_notification_emails)


class Page(TranslatableModel):
    class PageType(models.TextChoices):
        ABOUT = "about", "Chi siamo"
        CONTACT = "contact", "Contatti"
        FAQ = "faq", "FAQ"
        SHIPPING = "shipping", "Spedizioni"
        RETURNS = "returns", "Resi e rimborsi"
        PRIVACY = "privacy", "Privacy Policy"
        COOKIES = "cookies", "Cookie Policy"
        TERMS = "terms", "Termini e condizioni"

    translations = TranslatedFields(
        title=models.CharField(max_length=255),
        content=models.TextField(),
        meta_title=models.CharField(max_length=255, blank=True),
        meta_description=models.TextField(blank=True),
    )
    slug = models.SlugField(max_length=100, unique=True)
    page_type = models.CharField(max_length=20, choices=PageType.choices, unique=True)
    is_published = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["page_type"]

    def __str__(self):
        return self.safe_translation_getter("title", any_language=True) or self.slug


class FAQItem(TranslatableModel):
    translations = TranslatedFields(
        question=models.CharField(max_length=500),
        answer=models.TextField(),
    )
    sort_order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order"]

    def __str__(self):
        return self.safe_translation_getter("question", any_language=True) or f"FAQ {self.pk}"


class ContactSubmission(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True)
    subject = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} — {self.subject}"
