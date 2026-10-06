from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse


def send_order_confirmation(order) -> None:
    lang = order.language or "it"
    subject = (
        f"Conferma ordine {order.order_number} — SecurWork"
        if lang == "it"
        else f"Order confirmation {order.order_number} — SecurWork"
    )
    context = {
        "order": order,
        "items": order.items.all(),
        "lang": lang,
        "frontend_url": settings.FRONTEND_URL,
    }
    html = render_to_string("emails/order_confirmation.html", context)
    text = render_to_string("emails/order_confirmation.txt", context)

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[order.email],
    )
    msg.attach_alternative(html, "text/html")
    msg.send(fail_silently=False)


def _django_admin_order_url(order) -> str:
    path = reverse("admin:orders_order_change", args=[order.pk])
    if settings.DEBUG:
        return f"http://127.0.0.1:8000{path}"
    base = settings.FRONTEND_URL.rstrip("/")
    return f"{base}{path}" if base else path


def send_order_admin_notification(order) -> None:
    admin_email = getattr(settings, "ORDER_ADMIN_EMAIL", settings.CONTACT_EMAIL)
    subject = f"[SecurWork] Nuovo ordine {order.order_number} — €{order.total}"
    context = {
        "order": order,
        "items": order.items.all(),
        "admin_url": _django_admin_order_url(order),
    }
    html = render_to_string("emails/order_admin.html", context)
    text = render_to_string("emails/order_admin.txt", context)

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[admin_email],
    )
    msg.attach_alternative(html, "text/html")
    msg.send(fail_silently=True)
