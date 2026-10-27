from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import PickupLocation
from .pickup_serializers import PublicPickupLocationSerializer


class PickupLocationListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        locations = PickupLocation.objects.filter(is_active=True)
        serializer = PublicPickupLocationSerializer(locations, many=True)
        return Response(serializer.data)
