from rest_framework import serializers
from hashid_field import rest

from .models import Agent

from common.models import ThirdParty
from integrations.serializers import IntegrationSerializer


class AgentSerializer(serializers.ModelSerializer):
    id = rest.HashidSerializerCharField(read_only=True)
    thirdparty = serializers.ChoiceField(choices=ThirdParty.choices)
    integration = IntegrationSerializer(read_only=True)
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Agent
        fields = (
            "id",
            "name",
            "thirdparty",
            "instance_url",
            "integration",
            "user",
            "created_at",
            "updated_at",
        )

    def validate(self, attrs):
        if attrs.get("thirdparty", None) == ThirdParty.SALESFORCE and not attrs.get(
            "instance_url", None
        ):
            raise ValueError({"instance_url": "This field needed"})
        return attrs
