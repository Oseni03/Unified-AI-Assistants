from django.db import models

from langchain_core.messages import AIMessage, HumanMessage

from integrations.models import Agent
from common.models import AbstractBaseModel

# Create your models here.
class Message(AbstractBaseModel):
    text = models.CharField(max_length=350)
    is_ai = models.BooleanField(default=False)
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name="messages")

    @property
    def instance(self):
        if self.is_ai:
            return AIMessage(content=self.text)
        else:
            return HumanMessage(conetnt=self.text)