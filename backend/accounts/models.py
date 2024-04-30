import hashid_field
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, Group
from django.contrib.auth.models import BaseUserManager
from django.db import models

from .utils import ImageWithThumbnailMixin, UniqueFilePathGenerator

import logging 

logger = logging.getLogger(__name__)


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address")
        
        user = self.model(
            email=self.normalize_email(email).lower(),
            **extra_fields
        )
        user.set_password(password)
        user_group, _ = Group.objects.get_or_create(name="user")
        user.save(using=self._db)
        user.groups.add(user_group)
        return user

    def create_superuser(self, email, password, **extra_fields):
        user = self.create_user(
            email,
            password=password,
            **extra_fields
        )
        admin_group, _ = Group.objects.get_or_create(name="admin")
        user.is_superuser = True
        user.groups.add(admin_group)
        user.save(using=self._db)
        return user

    def filter_admins(self):
        return self.filter(groups__name="admin")


class User(AbstractBaseUser, PermissionsMixin):
    id = hashid_field.HashidAutoField(primary_key=True)
    created = models.DateTimeField(editable=False, auto_now_add=True)
    
    # User info
    email = models.EmailField(
        verbose_name="email address",
        max_length=255,
        unique=True,
    )
    first_name = models.CharField(max_length=40, blank=True, default='')
    last_name = models.CharField(max_length=40, blank=True, default='')
    avatar = models.OneToOneField(
        "UserAvatar", on_delete=models.SET_NULL, null=True, blank=True, related_name="user"
    )
    
    # db info
    is_confirmed = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_superuser = models.BooleanField(default=False)
    
    # 2 Factor Authentication info
    otp_enabled = models.BooleanField(default=False)
    otp_verified = models.BooleanField(default=False)
    otp_base32 = models.CharField(max_length=255, blank=True, default='')
    otp_auth_url = models.CharField(max_length=255, blank=True, default='')

    objects = UserManager()

    USERNAME_FIELD = "email"

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def is_staff(self):
        return self.is_superuser

    def has_group(self, name):
        return self.groups.filter(name=name).exists()


class UserAvatar(ImageWithThumbnailMixin, models.Model):
    original = models.ImageField(
        upload_to=UniqueFilePathGenerator("avatars"), null=True
    )
    thumbnail = models.ImageField(
        upload_to=UniqueFilePathGenerator("avatars/thumbnails"), null=True
    )

    THUMBNAIL_SIZE = (128, 128)
    ERROR_FIELD_NAME = "avatar"

    def __str__(self) -> str:
        return str(self.id)

