from rest_framework import serializers
from hashid_field import rest

from .models import Bot


class BotSerializer(serializers.ModelSerializer):
    id = rest.HashidSerializerCharField(read_only=True)
    
    class Meta:
        model = Bot 
        fields = "__all__"


class OAuthURLSerializer(serializers.Serializer):
    url = serializers.URLField(read_only=True)


class EventSerializer(serializers.Serializer):
    query = serializers.CharField()
    response = serializers.CharField(read_only=True)