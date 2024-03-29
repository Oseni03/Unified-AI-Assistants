import secrets
from django.utils.deconstruct import deconstructible
from django.core.files.base import ContentFile
from django.utils.translation import gettext as _
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework_simplejwt.tokens import AccessToken

from django.conf import settings
from django.urls import reverse

from PIL import Image
from io import BytesIO


@deconstructible
class UniqueFilePathGenerator:
    def __init__(self, path_prefix):
        self.path_prefix = path_prefix

    def __call__(self, _, filename, *args, **kwargs):
        return f"{self.path_prefix}/{secrets.token_hex(8)}/{filename}"


class ImageWithThumbnailMixin:
    FILE_FORMATS = {"jpg": "JPEG", "jpeg": "JPEG", "png": "PNG", "gif": "GIF", "webp": "WEBP"}

    def make_thumbnail(self):
        image = Image.open(self.original)
        image.thumbnail(self.THUMBNAIL_SIZE, Image.Resampling.LANCZOS)

        file_name = self.original.name.split("/")[-1]
        extension = self.original.name.split(".")[-1]
        file_format = self.FILE_FORMATS.get(extension.lower())
        if not file_format:
            raise ValidationError(
                {self.ERROR_FIELD_NAME: [_("Unsupported image file format.")]}
            )

        temp_thumbnail = BytesIO()
        image.save(temp_thumbnail, file_format)
        temp_thumbnail.seek(0)

        self.thumbnail.save(file_name, ContentFile(temp_thumbnail.read()), save=False)
        temp_thumbnail.close()

    def save(self, *args, **kwargs):
        if self.original:
            self.make_thumbnail()
        super().save(*args, **kwargs)


def set_auth_cookie(response, data):
    cookie_max_age = settings.COOKIE_MAX_AGE
    access = data.get(settings.ACCESS_TOKEN_COOKIE)
    refresh = data.get(settings.REFRESH_TOKEN_COOKIE)
    response.set_cookie(settings.ACCESS_TOKEN_COOKIE, access, max_age=cookie_max_age, httponly=True)

    if refresh:
        response.set_cookie(
            settings.REFRESH_TOKEN_COOKIE,
            refresh,
            max_age=cookie_max_age,
            httponly=True,
            path=reverse("jwt_token_refresh"),
        )

        response.set_cookie(
            settings.REFRESH_TOKEN_LOGOUT_COOKIE,
            refresh,
            max_age=cookie_max_age,
            httponly=True,
            path=reverse("logout"),
        )


def reset_auth_cookie(response):
    response.delete_cookie(settings.ACCESS_TOKEN_COOKIE)
    response.delete_cookie(settings.REFRESH_TOKEN_COOKIE)
    response.delete_cookie(settings.REFRESH_TOKEN_COOKIE, path=reverse("jwt_token_refresh"))
    response.delete_cookie(settings.REFRESH_TOKEN_LOGOUT_COOKIE, path=reverse("logout"))


def generate_otp_auth_token(user):
    otp_auth_token = AccessToken()
    otp_auth_token["user_id"] = str(user.id)
    otp_auth_token.set_exp(from_time=timezone.now(), lifetime=settings.OTP_AUTH_TOKEN_LIFETIME_MINUTES)

    return OTP_AUTH_TOKEN_LIFETIME_MINUTES