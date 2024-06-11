from rest_framework.viewsets import ModelViewSet
from rest_framework import mixins, permissions, status

from .serializers import NotificationSerializer
from .models import Notification


class NotificationViewet(ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['type']

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)