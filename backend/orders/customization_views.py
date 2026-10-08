import json

from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from store.customization import (
    CUSTOMIZATION_METHOD_CODES,
    product_has_customization,
    product_method_enabled,
)
from store.models import ProductVariant

from .models import LineItemCustomization
from .serializers import LineItemCustomizationSerializer


class CustomizationCreateView(APIView):
    """Upload logo + placement data; returns customization id for add-to-cart."""

    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        logo = request.FILES.get("logo")
        preview = request.FILES.get("preview")
        variant_id = request.data.get("variant_id")
        method = (request.data.get("method") or "").strip()
        raw_design = request.data.get("design_data", "{}")

        if not logo:
            return Response({"detail": "Logo file is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            variant = ProductVariant.objects.select_related("product").get(pk=variant_id, is_active=True)
        except (ProductVariant.DoesNotExist, TypeError, ValueError):
            return Response({"detail": "Invalid variant."}, status=status.HTTP_400_BAD_REQUEST)

        product = variant.product
        if not product_has_customization(product):
            return Response({"detail": "This product does not support customization."}, status=status.HTTP_400_BAD_REQUEST)

        if not method:
            method = LineItemCustomization.Method.EMBROIDERY_CHEST
        if method not in CUSTOMIZATION_METHOD_CODES:
            return Response({"detail": "Invalid customization method."}, status=status.HTTP_400_BAD_REQUEST)
        if not product_method_enabled(product, method):
            return Response(
                {"detail": "Selected customization method is not available for this product."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            design_data = json.loads(raw_design) if isinstance(raw_design, str) else raw_design
        except json.JSONDecodeError:
            return Response({"detail": "Invalid design_data JSON."}, status=status.HTTP_400_BAD_REQUEST)

        required = ("view", "x_pct", "y_pct", "width_pct", "height_pct")
        if not all(key in design_data for key in required):
            return Response({"detail": f"design_data must include: {', '.join(required)}"}, status=status.HTTP_400_BAD_REQUEST)

        customization = LineItemCustomization.objects.create(
            logo=logo,
            preview=preview,
            method=method,
            design_data=design_data,
        )
        return Response(
            LineItemCustomizationSerializer(customization, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )
