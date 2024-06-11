import datetime
from typing import Optional

import hashid_field

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from common.models import AbstractBaseModel

from . import managers


class NotificationTypes(models.TextChoices):
    FINISHED_CREDIT = "FINISHED_CREDIT", _("Finished Credit")


class Notification(AbstractBaseModel):
    user: settings.AUTH_USER_MODEL = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE) # type: ignore
    type: str = models.CharField(max_length=64, choices=NotificationTypes.choices)

    read_at: Optional[datetime.datetime] = models.DateTimeField(null=True, blank=True)

    data: dict = models.JSONField(default=dict)

    issuer: settings.AUTH_USER_MODEL = models.ForeignKey( # type: ignore
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name="notifications_issued"
    )

    objects = managers.NotificationManager()

    def __str__(self) -> str:
        return str(self.id)

    @property
    def is_read(self) -> bool:
        return self.read_at is not None

    @is_read.setter
    def is_read(self, val: bool):
        self.read_at = timezone.now() if val else None
