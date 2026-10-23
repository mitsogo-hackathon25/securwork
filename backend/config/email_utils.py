"""Shared outbound email helpers."""

import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

logger = logging.getLogger(__name__)


class EmailDeliveryError(Exception):
    """Transactional email could not be delivered."""


def smtp_is_configured() -> bool:
    return bool(
        settings.EMAIL_HOST
        and settings.EMAIL_HOST_USER
        and settings.EMAIL_HOST_PASSWORD
    )


def using_console_email_backend() -> bool:
    backend = (settings.EMAIL_BACKEND or "").lower()
    return "console" in backend or "dummy" in backend


def _backend_name() -> str:
    return (settings.EMAIL_BACKEND or "").lower()


def deliver_email(msg: EmailMultiAlternatives) -> None:
    backend = _backend_name()
    if "locmem" in backend:
        msg.send(fail_silently=False)
        return

    if using_console_email_backend() or not backend:
        if not settings.DEBUG:
            logger.error(
                "Password/reset email not sent: EMAIL_BACKEND is %s (not SMTP).",
                settings.EMAIL_BACKEND or "unset",
            )
            raise EmailDeliveryError(
                "Email service is not configured. Contact the site administrator."
            )
        logger.warning("Email dumped to console (DEBUG). Not delivered to inbox.")
        msg.send(fail_silently=False)
        return

    if "smtp" in backend and not smtp_is_configured():
        logger.error("SMTP email backend selected but EMAIL_HOST/USER/PASSWORD is incomplete.")
        raise EmailDeliveryError(
            "Email service is not configured. Contact the site administrator."
        )
    try:
        sent = msg.send(fail_silently=False)
    except Exception as exc:
        logger.exception("Email delivery failed to %s", msg.to)
        raise EmailDeliveryError(
            "Unable to send email at this time. Please try again later."
        ) from exc
    if not sent:
        logger.error("Email backend reported 0 messages sent to %s", msg.to)
        raise EmailDeliveryError(
            "Unable to send email at this time. Please try again later."
        )
