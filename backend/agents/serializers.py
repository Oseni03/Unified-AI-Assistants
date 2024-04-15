from rest_framework import serializers

from .models import Agent


class AgentSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    
    class Meta:
        model = Agent 
        exclude = ("created_at", "updated_at")
