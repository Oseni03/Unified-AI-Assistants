from rest_framework import serializers
from hashid_field import rest

from .models import Agent, FeedBack
from integrations.serializers import BotSerializer, IntegrationSerializer


class AgentSerializer(serializers.ModelSerializer):
    id = rest.HashidSerializerCharField(read_only=True)
    # user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    bots = BotSerializer(many=True, read_only=True)
    integration = IntegrationSerializer(many=False, read_only=True)
    
    class Meta:
        model = Agent 
        fields = ("id", "name", "is_public", "bots", "integration", "created_at")


class FeedBackSerializer(serializers.ModelSerializer):
    id = rest.HashidSerializerCharField(read_only=True)
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    
    class Meta:
        model = FeedBack 
        exclude = ("created_at", "updated_at")