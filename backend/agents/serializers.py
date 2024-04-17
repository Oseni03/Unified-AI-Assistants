from rest_framework import serializers
from hashid_field import rest

from .models import Agent


class AgentSerializer(serializers.ModelSerializer):
    id = rest.HashidSerializerCharField(read_only=True)
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    
    class Meta:
        model = Agent 
        exclude = ("created_at", "updated_at")
