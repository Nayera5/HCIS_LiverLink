"""
Notifications API (spec §14). Every endpoint only ever touches the signed-in user's own
notifications (self.notifications: every authenticated account, staff or patient).
"""
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import HasCapability

from .models import Notification
from .serializers import NotificationSerializer


class MyNotificationsView(generics.ListAPIView):
    """GET /api/notifications/me/?unread=true : the signed-in user's notifications + unread count."""

    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated, HasCapability('self.notifications')]

    def get_queryset(self):
        qs = Notification.objects.filter(user=self.request.user)
        if self.request.query_params.get('unread') == 'true':
            qs = qs.filter(is_read=False)
        return qs

    def list(self, request, *args, **kwargs):
        notifications = self.get_queryset()
        unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
        return Response({
            'unread_count': unread_count,
            'notifications': NotificationSerializer(notifications, many=True).data,
        })


class MarkNotificationReadView(APIView):
    """POST /api/notifications/<id>/read/ : own notification only."""

    permission_classes = [IsAuthenticated, HasCapability('self.notifications')]

    def post(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk, user=request.user)
        if not notification.is_read:
            notification.is_read = True
            notification.save(update_fields=['is_read'])
        return Response(NotificationSerializer(notification).data)


class MarkAllNotificationsReadView(APIView):
    """POST /api/notifications/read-all/ : marks every unread notification of the signed-in user."""

    permission_classes = [IsAuthenticated, HasCapability('self.notifications')]

    def post(self, request):
        updated = Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({'updated': updated}, status=status.HTTP_200_OK)
