from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from langchain.agents.agent import AgentExecutor

from accounts.models import User

# Create your models here.
class Agent(models.Model):
    class AgentType(models.TextChoices):
        PRIVATE = "PRIVATE", _("Private")
        PUBLIC = "PUBLIC", _("Public")

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="agents", null=True)
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=20, choices=AgentType.choices, default=AgentType.PRIVATE)
    data = models.JSONField(null=True) # agent.json() or agent.dict()
    slug = models.SlugField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.name)
    
    def invoke(self, input):
        pass

    def save(self, **kwargs) -> None:
        if not self.slug:
            self.slug = slugify(self.name)
        return super().save(**kwargs)