from rest_framework.response import Response
from rest_framework.views import APIView

from store.permissions import IsStaffUser

from .models import GlobalSettings
from .serializers import AdminGlobalSettingsSerializer


class AdminGlobalSettingsView(APIView):
    permission_classes = [IsStaffUser]

    def get(self, request):
        solo = GlobalSettings.get_solo()
        return Response(AdminGlobalSettingsSerializer(solo).data)

    def patch(self, request):
        solo = GlobalSettings.get_solo()
        serializer = AdminGlobalSettingsSerializer(solo, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
