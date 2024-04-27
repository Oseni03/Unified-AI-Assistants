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

    id = hashid_field.HashidAutoField(primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    def __str__(self):
        return "ah yes"


class ThirdParty(models.TextChoices):
    GMAIL = "gmail", _("Google Mail")
    GOOGLE_CALENDER = "google-calender", _("Google Calender")
    GOOGLE_DOCUMENT = "google-document", _("Google Document")
    GOOGLE_DRIVE = "google-drive", _("Google Drive")
    GOOGLE_SHEET = "google-sheet", _("Google Sheet")
    SALESFORCE = "salesforce", _("Salesforce")
    SLACK = "slack", _("Slack")


class State(AbstractBaseModel):
    is_used = models.BooleanField(default=False)
    state = models.CharField(max_length=300)
    thirdparty = models.CharField(max_length=25, choices=ThirdParty.choices)

    @classmethod
    def issue(cls, thirdparty: ThirdParty):
        state = State(
            state=hashlib.sha256(os.urandom(1024)).hexdigest(),
            thirdparty=thirdparty)
        state.save()
        return state.state
    
    @classmethod
    def consume(cls, state):
        state = State.objects.get(state=state)
        state.is_used = True
        state.save()