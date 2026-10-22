from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from config.email_utils import deliver_email


def send_password_reset_otp_email(
    user,
    code: str,
    lang: str = "it",
    to_email: str | None = None,
) -> None:
    lang = (lang or "it").split("-")[0].lower()
    if lang not in ("it", "en"):
        lang = getattr(settings, "PASSWORD_RESET_EMAIL_LANG", "it")

    subject = (
        "Codice per reimpostare la password — SecurWork"
        if lang == "it"
        else "Password reset code — SecurWork"
    )
    context = {
        "user": user,
        "code": code,
        "expiry_minutes": getattr(settings, "PASSWORD_RESET_OTP_EXPIRY_MINUTES", 15),
        "frontend_url": settings.FRONTEND_URL,
        "lang": lang,
    }
    html = render_to_string("emails/password_reset_otp.html", context)
    text = render_to_string("emails/password_reset_otp.txt", context)

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[to_email or user.email],
    )
    msg.attach_alternative(html, "text/html")
    deliver_email(msg)
