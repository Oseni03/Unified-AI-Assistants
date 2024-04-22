from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from langchain.agents.agent import AgentExecutor

from common.models import AbstractBaseModel, ThirdParty


# Create your models here.
class Agent(AbstractBaseModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="agents", null=True)
    name = models.CharField(max_length=255, default="AI assistant")
    access_token = models.CharField(max_length=255)
    refresh_token = models.CharField(max_length=255, null=True)
    token_uri = models.CharField(max_length=255, null=True)
    id_token = models.CharField(max_length=255)
    thirdparty = models.CharField(max_length=25, choices=ThirdParty.choices)
    is_public = models.BooleanField(default=False)
    data = models.JSONField(null=True) # agent.json() or agent.dict()

    def __str__(self):
        return str(self.name)
    
    def invoke(self, input):
        pass