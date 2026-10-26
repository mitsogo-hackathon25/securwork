from django.db.models import Count, Prefetch
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from store.permissions import IsStaffUser

from .models import SupportMessage, SupportTicket
from .serializers import (
    CreateSupportTicketSerializer,
    ReplySupportTicketSerializer,
    SupportTicketDetailSerializer,
    SupportTicketListSerializer,
)


class SupportTicketViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        message_qs = SupportMessage.objects.select_related("author").order_by("created_at")
        return (
            SupportTicket.objects.filter(user=self.request.user)
            .annotate(message_count=Count("messages"))
            .prefetch_related(Prefetch("messages", queryset=message_qs))
        )

    def list(self, request):
        qs = self.get_queryset()
        serializer = SupportTicketListSerializer(qs, many=True)
        return Response(serializer.data)

    def create(self, request):
        serializer = CreateSupportTicketSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        ticket = serializer.save()
        ticket = self.get_queryset().get(pk=ticket.pk)
        return Response(
            SupportTicketDetailSerializer(ticket).data,
            status=status.HTTP_201_CREATED,
        )

    def retrieve(self, request, pk=None):
        ticket = self.get_queryset().filter(pk=pk).first()
        if not ticket:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        if ticket.needs_user_attention:
            ticket.needs_user_attention = False
            ticket.save(update_fields=["needs_user_attention"])
        return Response(SupportTicketDetailSerializer(ticket).data)

    @action(detail=True, methods=["post"], url_path="reply")
    def reply(self, request, pk=None):
        ticket = self.get_queryset().filter(pk=pk).first()
        if not ticket:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = ReplySupportTicketSerializer(
            data=request.data,
            context={"request": request, "ticket": ticket},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        ticket.refresh_from_db()
        ticket = self.get_queryset().get(pk=ticket.pk)
        return Response(SupportTicketDetailSerializer(ticket).data)

    @action(detail=False, methods=["get"], url_path="unread-count")
    def unread_count(self, request):
        count = SupportTicket.objects.filter(user=request.user, needs_user_attention=True).count()
        return Response({"count": count})


class AdminSupportTicketViewSet(viewsets.GenericViewSet):
    permission_classes = [IsStaffUser]

    def get_queryset(self):
        return (
            SupportTicket.objects.select_related("user")
            .annotate(message_count=Count("messages"))
            .prefetch_related("messages", "messages__author")
        )

    def list(self, request):
        qs = self.get_queryset()
        serializer = SupportTicketListSerializer(qs, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        ticket = self.get_queryset().filter(pk=pk).first()
        if not ticket:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        if ticket.needs_staff_attention:
            ticket.needs_staff_attention = False
            ticket.save(update_fields=["needs_staff_attention"])
        return Response(SupportTicketDetailSerializer(ticket).data)

    @action(detail=True, methods=["post"], url_path="reply")
    def reply(self, request, pk=None):
        ticket = self.get_queryset().filter(pk=pk).first()
        if not ticket:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = ReplySupportTicketSerializer(
            data=request.data,
            context={"request": request, "ticket": ticket},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        ticket.refresh_from_db()
        ticket = self.get_queryset().get(pk=ticket.pk)
        return Response(SupportTicketDetailSerializer(ticket).data)

    @action(detail=True, methods=["patch"], url_path="status")
    def set_status(self, request, pk=None):
        ticket = self.get_queryset().filter(pk=pk).first()
        if not ticket:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        new_status = request.data.get("status")
        if new_status not in SupportTicket.Status.values:
            return Response({"detail": "Invalid status."}, status=status.HTTP_400_BAD_REQUEST)
        ticket.status = new_status
        ticket.save(update_fields=["status", "updated_at"])
        ticket = self.get_queryset().get(pk=ticket.pk)
        return Response(SupportTicketDetailSerializer(ticket).data)

    @action(detail=False, methods=["get"], url_path="unread-count")
    def unread_count(self, request):
        count = SupportTicket.objects.filter(needs_staff_attention=True).count()
        return Response({"count": count})
