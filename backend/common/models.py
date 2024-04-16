import hashid_field
from django.db import models


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