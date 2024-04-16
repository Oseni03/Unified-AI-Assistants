from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from langchain.agents.agent import AgentExecutor

from common.models import AbstractBaseModel


# Create your models here.
class Agent(AbstractBaseModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="agents", null=True)
    name = models.CharField(max_length=255)
    is_public = models.BooleanField(default=False)
    data = models.JSONField(null=True) # agent.json() or agent.dict()
    slug = models.SlugField()

    def __str__(self):
        return str(self.name)
    
    def invoke(self, input):
        pass

    def save(self, **kwargs) -> None:
        if not self.slug:
            self.slug = slugify(self.name)
        return super().save(**kwargs)