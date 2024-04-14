from rest_framework import exceptions, serializers, validators

from .models import Bot


class BotSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Bot 
        fields = "__all__"