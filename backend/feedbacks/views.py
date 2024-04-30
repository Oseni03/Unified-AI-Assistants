from rest_framework import generics, permissions, viewsets

from .models import FeedBack
from .serializers import FeedBackSerializer

# Create your views here.
class FeedBackViewset(viewsets.ModelViewSet):
    serializer_class = FeedBackSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['agent']

    def get_queryset(self):
        return FeedBack.objects.filter(user=self.request.user)