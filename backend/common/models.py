import datetime
import hashlib
import os
from uuid import uuid4
import hashid_field

from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


# Create your models here.
class AbstractBaseModel(models.Model):
    """
    An abstract model with fields/properties that should belong to all our models.
    """

    id: str = hashid_field.HashidAutoField(primary_key=True)
    created_at: datetime.datetime = models.DateTimeField(auto_now_add=True)
    updated_at: datetime.datetime = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    def __str__(self):
        return "ah yes"


class ThirdParty(models.TextChoices):
    GOOGLE_WORKSPACE = "google-workspace", _("Google Workspace")
    ZOHO_WORKSPACE = "zoho-workspace", _("Zoho Workspace")
    SALESFORCE = "salesforce", _("Salesforce")
    SLACK = "slack", _("Slack")
