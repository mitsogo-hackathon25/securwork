from rest_framework import serializers

from .models import PickupLocation


class PickupLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PickupLocation
        fields = [
            "id",
            "name",
            "address",
            "city",
            "postcode",
            "country",
            "phone",
            "notes",
            "is_active",
            "sort_order",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class PublicPickupLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PickupLocation
        fields = ["id", "name", "address", "city", "postcode", "country", "phone", "notes"]
