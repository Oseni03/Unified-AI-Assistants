from rest_framework import serializers
from hashid_field import rest

from .models import Bot, Integration


class IntegrationSerializer(serializers.ModelSerializer):
    id = rest.HashidSerializerCharField(read_only=True)
    url = serializers.CharField(source="get_absolute_url", read_only=True)

    class Meta:
        model = Integration
        fields = ("id", "thirdparty", "is_chat_app", "url")


class BotSerializer(serializers.ModelSerializer):
    id = rest.HashidSerializerCharField(read_only=True)
    
    class Meta:
        model = Bot 
        fields = "__all__"


class EventSerializer(serializers.Serializer):
    query = serializers.CharField()
    response = serializers.CharField(read_only=True)