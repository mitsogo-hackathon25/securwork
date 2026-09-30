import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models

from store.models import ProductVariant


class Cart(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE, related_name="carts"
    )
    session_key = models.CharField(max_length=40, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"Cart {self.pk}"

    @property
    def total(self) -> Decimal:
        return sum(item.line_total for item in self.items.select_related("variant"))


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name="items", on_delete=models.CASCADE)
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("cart", "variant")

    @property
    def line_total(self) -> Decimal:
        return self.variant.effective_price * self.quantity


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "In attesa di pagamento"
        PROCESSING = "processing", "In lavorazione"
        SHIPPED = "shipped", "Spedito"
        DELIVERED = "delivered", "Consegnato"
        CANCELLED = "cancelled", "Annullato"
        REFUNDED = "refunded", "Rimborsato"

    class PaymentMethod(models.TextChoices):
        STRIPE = "stripe", "Carta (Stripe)"
        BANK_TRANSFER = "bank_transfer", "Bonifico bancario"
        MANUAL = "manual", "Manuale"

    class PaymentStatus(models.TextChoices):
        PENDING = "pending", "In attesa"
        PAID = "paid", "Pagato"
        FAILED = "failed", "Fallito"
        REFUNDED = "refunded", "Rimborsato"

    order_number = models.CharField(max_length=32, unique=True, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="orders"
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True)

    billing_first_name = models.CharField(max_length=100)
    billing_last_name = models.CharField(max_length=100)
    billing_company = models.CharField(max_length=200, blank=True)
    billing_address = models.CharField(max_length=255)
    billing_city = models.CharField(max_length=100)
    billing_postcode = models.CharField(max_length=20)
    billing_country = models.CharField(max_length=2, default="IT")
    billing_vat = models.CharField(max_length=50, blank=True, help_text="P.IVA / VAT number")

    shipping_first_name = models.CharField(max_length=100)
    shipping_last_name = models.CharField(max_length=100)
    shipping_address = models.CharField(max_length=255)
    shipping_city = models.CharField(max_length=100)
    shipping_postcode = models.CharField(max_length=20)
    shipping_country = models.CharField(max_length=2, default="IT")

    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    total = models.DecimalField(max_digits=10, decimal_places=2)

    coupon_code = models.CharField(max_length=50, blank=True)
    notes = models.TextField(blank=True)
    language = models.CharField(max_length=2, default="it")

    payment_method = models.CharField(
        max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.STRIPE
    )
    payment_status = models.CharField(
        max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING
    )
    stripe_session_id = models.CharField(max_length=255, blank=True)
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.order_number

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = f"SW-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    variant = models.ForeignKey(ProductVariant, on_delete=models.PROTECT)
    product_name = models.CharField(max_length=255)
    sku = models.CharField(max_length=100)
    size = models.CharField(max_length=50, blank=True)
    color = models.CharField(max_length=50, blank=True)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()
    line_total = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.sku} x{self.quantity}"


class Coupon(models.Model):
    code = models.CharField(max_length=50, unique=True)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    max_uses = models.PositiveIntegerField(null=True, blank=True)
    used_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_until = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.code
