from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from accounts.models import User
from common.models import AbstractBaseModel
from integrations.models import Agent


# Create your models here.
class FeedBack(AbstractBaseModel):
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name="feedbacks")
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="feedbacks")
    message = models.TextField()
    like = models.BooleanField(default=False)
    dislike = models.BooleanField(default=False)

    def __str__(self):
        return str(f"Agent: {self.id} - By: {self.user}")