from django.db import models

from accounts.models import User
from common.models import AbstractBaseModel
from agents.models import Agent
from integrations.models import Integration


# Create your models here.
class Ticket(AbstractBaseModel):
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('closed', 'Closed'),
        ('pending', 'Pending'),
    ]
    TYPE_CHOICES = [
        ('issue', 'Issue'),
        ('feedback', 'Feedback'),
    ]
    title = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='open')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="tickets", null=True)
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    integration = models.ForeignKey(Integration, on_delete=models.CASCADE)
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='feedback')
    rating = models.IntegerField(null=True, blank=True)
    comment = models.TextField(null=True, blank=True)

    def __str__(self):
        return str(f"Title: {self.title} - Thirdparty: {self.agent.thirdparty}")