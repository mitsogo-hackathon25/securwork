"""Password reset via one-time code emailed to the user's registered address."""

import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils import timezone

from .emails import send_password_reset_otp_email
from .models import PasswordResetOTP

User = get_user_model()
logger = logging.getLogger(__name__)

GENERIC_REQUEST_MESSAGE = (
    "If an account exists for this email, you will receive a verification code shortly."
)
GENERIC_CONFIRM_FAILURE = "Invalid or expired verification code."


def _otp_expiry_minutes() -> int:
    return int(getattr(settings, "PASSWORD_RESET_OTP_EXPIRY_MINUTES", 15))


def _max_requests_per_hour() -> int:
    return int(getattr(settings, "PASSWORD_RESET_MAX_REQUESTS_PER_HOUR", 5))


def _max_verify_attempts() -> int:
    return int(getattr(settings, "PASSWORD_RESET_MAX_VERIFY_ATTEMPTS", 5))


def request_password_reset(email: str) -> str:
    """
    Create and email an OTP for the user with this registered email.
    Always returns the same user-facing message (no email enumeration).
    """
    normalized = (email or "").strip().lower()
    if not normalized:
        return GENERIC_REQUEST_MESSAGE

    user = User.objects.filter(email__iexact=normalized).first()
    if not user or not (user.email or "").strip():
        logger.info("Password reset requested for unknown or empty-email account.")
        return GENERIC_REQUEST_MESSAGE

    since = timezone.now() - timedelta(hours=1)
    recent_count = PasswordResetOTP.objects.filter(user=user, created_at__gte=since).count()
    if recent_count >= _max_requests_per_hour():
        logger.warning("Password reset rate limit for user id=%s", user.pk)
        return GENERIC_REQUEST_MESSAGE

    PasswordResetOTP.objects.filter(user=user, used=False).update(used=True)

    code = f"{secrets.randbelow(10**6):06d}"
    PasswordResetOTP.objects.create(
        user=user,
        email_snapshot=user.email,
        code_hash=make_password(code),
        expires_at=timezone.now() + timedelta(minutes=_otp_expiry_minutes()),
    )

    try:
        send_password_reset_otp_email(user, code)
    except Exception:
        logger.exception("Failed to send password reset email for user id=%s", user.pk)
    return GENERIC_REQUEST_MESSAGE


def confirm_password_reset(email: str, otp: str, new_password: str) -> None:
    normalized = (email or "").strip().lower()
    code = (otp or "").strip()
    if not normalized or not code:
        raise ValidationError(GENERIC_CONFIRM_FAILURE)

    user = User.objects.filter(email__iexact=normalized).first()
    if not user:
        raise ValidationError(GENERIC_CONFIRM_FAILURE)

    record = (
        PasswordResetOTP.objects.filter(
            user=user,
            used=False,
            expires_at__gt=timezone.now(),
        )
        .order_by("-created_at")
        .first()
    )
    if not record:
        raise ValidationError(GENERIC_CONFIRM_FAILURE)

    if record.verify_attempts >= _max_verify_attempts():
        record.used = True
        record.save(update_fields=["used"])
        raise ValidationError(GENERIC_CONFIRM_FAILURE)

    if not check_password(code, record.code_hash):
        record.verify_attempts += 1
        record.save(update_fields=["verify_attempts"])
        raise ValidationError(GENERIC_CONFIRM_FAILURE)

    validate_password(new_password, user)
    user.set_password(new_password)
    user.save(update_fields=["password"])

    PasswordResetOTP.objects.filter(user=user, used=False).update(used=True)
    record.used = True
    record.save(update_fields=["used"])
