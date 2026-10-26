from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import SupportMessage, SupportTicket

User = get_user_model()


class SupportMessageSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = SupportMessage
        fields = ["id", "body", "is_staff_reply", "author_name", "created_at"]
        read_only_fields = fields

    def get_author_name(self, obj):
        if obj.is_staff_reply:
            return "SecurWork Support"
        return obj.author.get_full_name() or obj.author.username


class SupportTicketListSerializer(serializers.ModelSerializer):
    last_message_preview = serializers.SerializerMethodField()
    last_message_is_staff = serializers.SerializerMethodField()
    message_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = SupportTicket
        fields = [
            "id",
            "subject",
            "status",
            "needs_user_attention",
            "needs_staff_attention",
            "created_at",
            "updated_at",
            "last_message_preview",
            "last_message_is_staff",
            "message_count",
        ]

    def _last_message(self, obj):
        prefetched = getattr(obj, "_prefetched_objects_cache", {}).get("messages")
        if prefetched is not None:
            if not prefetched:
                return None
            return max(prefetched, key=lambda m: m.created_at)
        return obj.messages.order_by("-created_at").first()

    def get_last_message_preview(self, obj):
        last = self._last_message(obj)
        if not last:
            return ""
        text = last.body.strip().replace("\n", " ")
        return text[:120] + ("…" if len(text) > 120 else "")

    def get_last_message_is_staff(self, obj):
        last = self._last_message(obj)
        return bool(last and last.is_staff_reply)


class SupportTicketDetailSerializer(SupportTicketListSerializer):
    messages = SupportMessageSerializer(many=True, read_only=True)
    user_display = serializers.SerializerMethodField()

    class Meta(SupportTicketListSerializer.Meta):
        fields = SupportTicketListSerializer.Meta.fields + ["messages", "user_display"]

    def get_user_display(self, obj):
        return obj.user.get_full_name() or obj.user.username


class CreateSupportTicketSerializer(serializers.Serializer):
    subject = serializers.CharField(max_length=200)
    message = serializers.CharField()

    def create(self, validated_data):
        user = self.context["request"].user
        ticket = SupportTicket.objects.create(
            user=user,
            subject=validated_data["subject"].strip(),
            needs_staff_attention=True,
            needs_user_attention=False,
        )
        SupportMessage.objects.create(
            ticket=ticket,
            author=user,
            body=validated_data["message"].strip(),
            is_staff_reply=False,
        )
        return ticket


class ReplySupportTicketSerializer(serializers.Serializer):
    message = serializers.CharField()

    def create(self, validated_data):
        ticket = self.context["ticket"]
        request = self.context["request"]
        is_staff_reply = bool(request.user.is_staff)
        if is_staff_reply:
            ticket.needs_user_attention = True
            ticket.needs_staff_attention = False
        else:
            ticket.needs_staff_attention = True
            ticket.needs_user_attention = False
        ticket.save(update_fields=["needs_user_attention", "needs_staff_attention", "updated_at"])
        return SupportMessage.objects.create(
            ticket=ticket,
            author=request.user,
            body=validated_data["message"].strip(),
            is_staff_reply=is_staff_reply,
        )
