from rest_framework import mixins, permissions, status
from rest_framework.viewsets import GenericViewSet

from .models import Integration
from .serializers import IntegrationSerializer


class IntegrationViewSet(mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    GenericViewSet
):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = IntegrationSerializer
    filterset_fields = ['is_chat_app']

    def get_queryset(self):
        return Integration.objects.filter(user=self.request.user)