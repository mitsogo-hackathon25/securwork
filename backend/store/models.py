from decimal import Decimal

from django.db import models
from django.utils.text import slugify
from parler.models import TranslatableModel, TranslatedFields


class Category(TranslatableModel):
    class Section(models.TextChoices):
        WORKWEAR = "workwear", "Abbigliamento da lavoro"
        PROFESSIONAL = "professional", "Abbigliamento professionale"

    translations = TranslatedFields(
        name=models.CharField(max_length=200),
        description=models.TextField(blank=True),
    )
    slug = models.SlugField(max_length=200, unique=True)
    section = models.CharField(max_length=20, choices=Section.choices, default=Section.WORKWEAR)
    parent = models.ForeignKey(
        "self", null=True, blank=True, related_name="children", on_delete=models.CASCADE
    )
    image = models.ImageField(upload_to="categories/", blank=True, null=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "slug"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.safe_translation_getter("name", any_language=True) or self.slug

    def save(self, *args, **kwargs):
        if not self.slug:
            name = self.safe_translation_getter("name", language_code="it") or "category"
            self.slug = slugify(name)
        super().save(*args, **kwargs)


class Product(TranslatableModel):
    translations = TranslatedFields(
        name=models.CharField(max_length=255),
        short_description=models.TextField(blank=True),
        description=models.TextField(blank=True),
        meta_title=models.CharField(max_length=255, blank=True),
        meta_description=models.TextField(blank=True),
    )
    slug = models.SlugField(max_length=255, unique=True)
    sku = models.CharField(max_length=100, unique=True, help_text="Base SKU for simple products")
    brand = models.CharField(max_length=100, blank=True, help_text="Manufacturer / brand name")
    categories = models.ManyToManyField(Category, related_name="products", blank=True)
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    is_new_arrival = models.BooleanField(default=False)
    is_bestseller = models.BooleanField(default=False)
    allows_customization = models.BooleanField(
        default=False,
        help_text="Customers can upload a logo and position it on this product.",
    )
    mockup_front = models.ImageField(
        upload_to="mockups/",
        blank=True,
        null=True,
        help_text="Front mockup image for the logo customizer (falls back to primary product photo).",
    )
    customization_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Extra charge per customized item (EUR).",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.safe_translation_getter("name", any_language=True) or self.slug

    @property
    def is_variable(self):
        return self.variants.filter(is_active=True).count() > 1

    @property
    def min_price(self) -> Decimal | None:
        variants = self.variants.filter(is_active=True)
        if not variants.exists():
            return None
        return min(v.effective_price for v in variants)

    @property
    def in_stock(self) -> bool:
        return self.variants.filter(is_active=True, stock_quantity__gt=0).exists()


class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name="images", on_delete=models.CASCADE)
    image = models.ImageField(upload_to="products/", blank=True, null=True)
    external_url = models.URLField(max_length=500, blank=True)
    alt_text = models.CharField(max_length=255, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_primary = models.BooleanField(default=False)

    class Meta:
        ordering = ["sort_order"]

    def display_url(self, request=None) -> str | None:
        if self.image:
            url = self.image.url
            if request and url.startswith("/"):
                return request.build_absolute_uri(url)
            return url
        return self.external_url or None

    def __str__(self):
        return f"Image for {self.product_id}"


class ProductVariant(models.Model):
    product = models.ForeignKey(Product, related_name="variants", on_delete=models.CASCADE)
    sku = models.CharField(max_length=100, unique=True)
    size = models.CharField(max_length=50, blank=True)
    color = models.CharField(max_length=50, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    sale_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    stock_quantity = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["size", "color"]

    def __str__(self):
        parts = [self.sku]
        if self.size:
            parts.append(self.size)
        if self.color:
            parts.append(self.color)
        return " / ".join(parts)

    @property
    def effective_price(self) -> Decimal:
        if self.sale_price is not None and self.sale_price < self.price:
            return self.sale_price
        return self.price

    @property
    def in_stock(self) -> bool:
        return self.stock_quantity > 0

    @property
    def is_low_stock(self) -> bool:
        from django.conf import settings
        threshold = getattr(settings, "SECURWORK_LOW_STOCK_THRESHOLD", 5)
        return 0 < self.stock_quantity <= threshold


class Brand(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:120] or "brand"
        super().save(*args, **kwargs)


class Color(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:120] or "color"
        super().save(*args, **kwargs)
