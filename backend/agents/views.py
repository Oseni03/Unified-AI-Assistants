from rest_framework import status, generics, permissions
from rest_framework.response import Response

from .serializers import AgentSerializer
from .models import Agent

# Create your views here.
class AgentAPIView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AgentSerializer

    def get_queryset(self):
        return Agent.objects.filter(user=self.request.user)
    