from django.conf import settings
from django.core.mail import send_mail
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .models import FAQItem, Page
from .serializers import ContactSerializer, FAQSerializer, PageSerializer


class SiteConfigView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({
            "company_name": settings.SECURWORK_COMPANY_NAME,
            "company_vat": settings.SECURWORK_COMPANY_VAT,
            "company_address": settings.SECURWORK_COMPANY_ADDRESS,
            "company_city": settings.SECURWORK_COMPANY_CITY,
            "company_phone": settings.SECURWORK_COMPANY_PHONE,
            "contact_email": settings.CONTACT_EMAIL,
            "map_lat": settings.SECURWORK_MAP_LAT,
            "map_lng": settings.SECURWORK_MAP_LNG,
        })


class PageDetailView(generics.RetrieveAPIView):
    queryset = Page.objects.filter(is_published=True)
    serializer_class = PageSerializer
    lookup_field = "page_type"

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["lang"] = self.request.query_params.get("lang", "it")
        return ctx


class FAQListView(generics.ListAPIView):
    queryset = FAQItem.objects.filter(is_published=True)
    serializer_class = FAQSerializer
    pagination_class = None

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["lang"] = self.request.query_params.get("lang", "it")
        return ctx


class ContactView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "contact"

    def post(self, request):
        serializer = ContactSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if serializer.validated_data.get("website"):
            return Response({"detail": "Message sent."}, status=status.HTTP_201_CREATED)

        submission = serializer.save()
        send_mail(
            subject=f"[SecurWork] {submission.subject}",
            message=(
                f"Nome: {submission.name}\n"
                f"Email: {submission.email}\n"
                f"Telefono: {submission.phone}\n\n"
                f"{submission.message}"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.CONTACT_EMAIL],
            fail_silently=True,
        )
        return Response({"detail": "Message sent."}, status=status.HTTP_201_CREATED)
