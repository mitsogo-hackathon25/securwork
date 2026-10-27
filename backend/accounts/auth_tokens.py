import re

from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

from .messages import api_message, lang_from_serializer_context

User = get_user_model()


def unique_username_from_email(email: str) -> str:
    local = (email.split("@")[0] if email else "user").strip()[:30]
    base = re.sub(r"[^\w.@+-]", "", local) or "user"
    username = base
    counter = 1
    while User.objects.filter(username__iexact=username).exists():
        suffix = str(counter)
        username = f"{base[: max(1, 30 - len(suffix))]}{suffix}"
        counter += 1
    return username


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Log in with email or username + password (JWT)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        username_field = self.username_field
        self.fields[username_field].required = False
        self.fields[username_field].allow_blank = True
        self.fields["email"] = serializers.EmailField(required=False, allow_blank=True, write_only=True)

    def validate(self, attrs):
        request = self.context.get("request")
        lang = "it"
        if request is not None:
            lang = request.GET.get("lang") or getattr(request, "LANGUAGE_CODE", "it") or "it"

        email = (attrs.pop("email", "") or "").strip().lower()
        username = (attrs.get(self.username_field) or "").strip()
        password = attrs.get("password")

        if not email and not username:
            raise serializers.ValidationError({
                "detail": api_message("login_invalid", lang),
            })

        user = None
        if email:
            user = User.objects.filter(email__iexact=email).first()
        if user is None and username:
            user = User.objects.filter(username__iexact=username).first()

        if user is None or not user.check_password(password):
            raise serializers.ValidationError({
                "detail": api_message("login_invalid", lang),
            })
        if not user.is_active:
            raise serializers.ValidationError({
                "detail": api_message("login_inactive", lang),
            })
        attrs[self.username_field] = user.get_username()
        return super().validate(attrs)


class EmailTokenObtainPairView(TokenObtainPairView):
    serializer_class = EmailTokenObtainPairSerializer
