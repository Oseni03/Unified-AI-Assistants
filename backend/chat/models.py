from django.db import models

from langchain_core.messages import AIMessage, HumanMessage

from agents.models import Agent
from common.models import AbstractBaseModel

# Create your models here.
class ChatMessage(AbstractBaseModel):
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE)
    message = models.TextField()
    is_ai = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    @property
    def instance(self):
        if self.is_ai:
            return AIMessage(content=self.text)
        else:
            return HumanMessage(conetnt=self.text)