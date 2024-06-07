from rest_framework import serializers
from hashid_field import rest

from .models import Integration


class IntegrationSerializer(serializers.ModelSerializer):
    id = rest.HashidSerializerCharField(read_only=True)
    
    class Meta:
        model = Integration
        fields = '__all__'