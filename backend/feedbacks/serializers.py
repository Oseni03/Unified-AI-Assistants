from rest_framework import serializers
from hashid_field import rest

from agents.serializers import AgentSerializer
from integrations.serializers import IntegrationSerializer

from .models import Ticket


class TicketSerializer(serializers.ModelSerializer):
    id = rest.HashidSerializerCharField(read_only=True)
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    
    class Meta:
        model = Ticket
        fields = ("id", "title", "description", "user")