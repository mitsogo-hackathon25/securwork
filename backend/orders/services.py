from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from store.models import ProductVariant

from .models import Cart, CartItem, Coupon, Order, OrderItem


def get_or_create_cart(request) -> Cart:
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        return cart
    session_key = request.session.session_key
    if not session_key:
        request.session.create()
        session_key = request.session.session_key
    cart, _ = Cart.objects.get_or_create(session_key=session_key, user=None)
    return cart


def calculate_tax(subtotal: Decimal) -> Decimal:
    rate = Decimal(getattr(settings, "SECURWORK_VAT_RATE", "22.00")) / Decimal("100")
    return (subtotal * rate).quantize(Decimal("0.01"))


def calculate_shipping(subtotal: Decimal) -> Decimal:
    free_threshold = Decimal(getattr(settings, "SECURWORK_FREE_SHIPPING_THRESHOLD", "100.00"))
    flat_rate = Decimal(getattr(settings, "SECURWORK_SHIPPING_FLAT_RATE", "5.99"))
    if subtotal >= free_threshold:
        return Decimal("0.00")
    return flat_rate


def apply_coupon(code: str, subtotal: Decimal) -> tuple[Decimal, Coupon | None]:
    if not code:
        return Decimal("0.00"), None
    try:
        coupon = Coupon.objects.get(code__iexact=code, is_active=True)
    except Coupon.DoesNotExist:
        return Decimal("0.00"), None
    now = timezone.now()
    if coupon.valid_from and now < coupon.valid_from:
        return Decimal("0.00"), None
    if coupon.valid_until and now > coupon.valid_until:
        return Decimal("0.00"), None
    if coupon.max_uses and coupon.used_count >= coupon.max_uses:
        return Decimal("0.00"), None
    if subtotal < coupon.min_order_amount:
        return Decimal("0.00"), None
    if coupon.discount_percent:
        return (subtotal * coupon.discount_percent / Decimal("100")).quantize(Decimal("0.01")), coupon
    if coupon.discount_amount:
        return min(coupon.discount_amount, subtotal), coupon
    return Decimal("0.00"), None


@transaction.atomic
def create_order_from_cart(cart: Cart, data: dict, user=None) -> Order:
    items = list(cart.items.select_related("variant", "variant__product", "customization"))
    if not items:
        raise ValueError("Cart is empty.")

    for item in items:
        variant = ProductVariant.objects.select_for_update().get(pk=item.variant_id)
        if variant.stock_quantity < item.quantity:
            raise ValueError(f"Insufficient stock for {variant.sku}.")

    subtotal = sum(item.line_total for item in items)
    discount, coupon = apply_coupon(data.get("coupon_code", ""), subtotal)
    taxable = subtotal - discount
    tax = calculate_tax(taxable)
    shipping = calculate_shipping(taxable)
    total = taxable + tax + shipping

    payment_method = data.get("payment_method", Order.PaymentMethod.STRIPE)
    if payment_method not in Order.PaymentMethod.values:
        payment_method = Order.PaymentMethod.STRIPE

    order = Order.objects.create(
        user=user,
        email=data["email"],
        phone=data.get("phone", ""),
        billing_first_name=data["billing_first_name"],
        billing_last_name=data["billing_last_name"],
        billing_company=data.get("billing_company", ""),
        billing_address=data["billing_address"],
        billing_city=data["billing_city"],
        billing_postcode=data["billing_postcode"],
        billing_country=data.get("billing_country", "IT"),
        billing_vat=data.get("billing_vat", ""),
        shipping_first_name=data["shipping_first_name"],
        shipping_last_name=data["shipping_last_name"],
        shipping_address=data["shipping_address"],
        shipping_city=data["shipping_city"],
        shipping_postcode=data["shipping_postcode"],
        shipping_country=data.get("shipping_country", "IT"),
        subtotal=subtotal,
        shipping_cost=shipping,
        tax_amount=tax,
        discount_amount=discount,
        total=total,
        coupon_code=data.get("coupon_code", ""),
        notes=data.get("notes", ""),
        language=data.get("language", "it"),
        payment_method=payment_method,
    )

    lang = data.get("language", "it")
    for item in items:
        variant = item.variant
        product_name = variant.product.safe_translation_getter("name", language_code=lang, any_language=True)
        OrderItem.objects.create(
            order=order,
            variant=variant,
            product_name=product_name or variant.sku,
            sku=variant.sku,
            size=variant.size,
            color=variant.color,
            unit_price=item.unit_price,
            quantity=item.quantity,
            line_total=item.line_total,
            customization=item.customization,
        )
        variant.stock_quantity -= item.quantity
        variant.save(update_fields=["stock_quantity"])

    if coupon:
        coupon.used_count += 1
        coupon.save(update_fields=["used_count"])

    cart.items.all().delete()
    return order
