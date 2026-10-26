from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .messages import api_message, lang_from_serializer_context
from .models import UserProfile
from config.email_utils import EmailDeliveryError

from .password_reset import confirm_password_reset, request_password_reset

User = get_user_model()


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ["phone", "company", "vat_number"]


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)
    is_staff = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "is_staff", "profile"]
        read_only_fields = ["id", "username", "is_staff"]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name", "password", "password_confirm"]

    def validate_username(self, value):
        username = (value or "").strip()
        if User.objects.filter(username__iexact=username).exists():
            lang = lang_from_serializer_context(self.context)
            raise serializers.ValidationError(api_message("username_taken", lang))
        return username

    def validate_email(self, value):
        email = (value or "").strip().lower()
        if not email:
            lang = lang_from_serializer_context(self.context)
            raise serializers.ValidationError(api_message("email_invalid", lang))
        if User.objects.filter(email__iexact=email).exists():
            lang = lang_from_serializer_context(self.context)
            raise serializers.ValidationError(api_message("email_taken", lang))
        return email

    def validate_password(self, value):
        user = User(
            username=(self.initial_data.get("username") or "").strip(),
            email=(self.initial_data.get("email") or "").strip().lower(),
            first_name=(self.initial_data.get("first_name") or "").strip(),
            last_name=(self.initial_data.get("last_name") or "").strip(),
        )
        try:
            validate_password(value, user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages)) from exc
        return value

    def validate(self, data):
        if data["password"] != data["password_confirm"]:
            lang = lang_from_serializer_context(self.context)
            raise serializers.ValidationError({
                "password_confirm": api_message("password_mismatch", lang),
            })
        return data

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        return User.objects.create_user(**validated_data)


class ProfileUpdateSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source="user.first_name", required=False)
    last_name = serializers.CharField(source="user.last_name", required=False)
    email = serializers.EmailField(source="user.email", required=False)
    phone = serializers.CharField(required=False, allow_blank=True)
    company = serializers.CharField(required=False, allow_blank=True)
    vat_number = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = UserProfile
        fields = ["first_name", "last_name", "email", "phone", "company", "vat_number"]

    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", {})
        for attr, value in user_data.items():
            setattr(instance.user, attr, value)
        instance.user.save()
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        return (value or "").strip().lower()

    def save(self, **kwargs):
        lang = self.context.get("lang", "it")
        try:
            return request_password_reset(self.validated_data["email"], lang=lang)
        except EmailDeliveryError as exc:
            raise serializers.ValidationError({"detail": str(exc)}) from exc


class PasswordResetConfirmSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(min_length=4, max_length=12)
    password = serializers.CharField(write_only=True)
    password_confirm = serializers.CharField(write_only=True)

    def validate_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages)) from exc
        return value

    def validate(self, data):
        if data["password"] != data["password_confirm"]:
            lang = lang_from_serializer_context(self.context)
            raise serializers.ValidationError({
                "password_confirm": api_message("password_mismatch", lang),
            })
        return data

    def save(self, **kwargs):
        try:
            confirm_password_reset(
                self.validated_data["email"],
                self.validated_data["otp"],
                self.validated_data["password"],
            )
        except DjangoValidationError as exc:
            message = exc.messages[0] if getattr(exc, "messages", None) else str(exc)
            raise serializers.ValidationError({"otp": message}) from exc
