from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from store.home_media_specs import HERO_IMAGE_DIMENSIONS_LABEL
from store.permissions import IsStaffUser

from .models import GlobalSettings
from .serializers import AdminGlobalSettingsSerializer


def _hero_image_url(request, solo: GlobalSettings) -> str | None:
    if not solo.hero_image:
        return None
    return request.build_absolute_uri(solo.hero_image.url)


class AdminGlobalSettingsView(APIView):
    permission_classes = [IsStaffUser]

    def get(self, request):
        solo = GlobalSettings.get_solo()
        return Response(
            AdminGlobalSettingsSerializer(solo, context={"request": request}).data,
        )

    def patch(self, request):
        solo = GlobalSettings.get_solo()
        serializer = AdminGlobalSettingsSerializer(
            solo,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class AdminHeroImageView(APIView):
    permission_classes = [IsStaffUser]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        solo = GlobalSettings.get_solo()
        image_file = request.FILES.get("hero_image")
        if not image_file:
            return Response(
                {"detail": "Seleziona un file (campo hero_image)."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if solo.hero_image:
            solo.hero_image.delete(save=False)
        solo.hero_image = image_file
        solo.save(update_fields=["hero_image", "updated_at"])
        return Response({
            "hero_image_url": _hero_image_url(request, solo),
            "hero_image_dimensions_hint": HERO_IMAGE_DIMENSIONS_LABEL,
            "detail": "Immagine hero salvata.",
        })

    def delete(self, request):
        solo = GlobalSettings.get_solo()
        if solo.hero_image:
            solo.hero_image.delete(save=True)
        return Response({"hero_image_url": None, "detail": "Immagine hero rimossa."})
