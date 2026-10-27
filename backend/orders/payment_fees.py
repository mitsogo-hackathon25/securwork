"""Customer-visible payment processing fees (passed through at checkout)."""

from decimal import Decimal

from django.conf import settings


def calculate_paypal_customer_fee(net_amount: Decimal) -> Decimal:
    """
    Gross-up so the merchant receives about net_amount after PayPal takes
    percent + fixed on the amount charged (Standard Domestic EEA: 3.4% + €0.35).
    """
    net = Decimal(net_amount).quantize(Decimal("0.01"))
    if net <= 0:
        return Decimal("0.00")

    percent = Decimal(getattr(settings, "PAYPAL_CUSTOMER_FEE_PERCENT", "3.4")) / Decimal("100")
    fixed = Decimal(getattr(settings, "PAYPAL_CUSTOMER_FEE_FIXED", "0.35"))
    gross = ((net + fixed) / (Decimal("1") - percent)).quantize(Decimal("0.01"))
    return (gross - net).quantize(Decimal("0.01"))
