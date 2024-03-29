from typing import Tuple

import pyotp
from accounts.constants import OTPErrors
from accounts.models import User
from django.conf import settings


def generate_otp(user: User) -> Tuple[str, str]:
    otp_base32 = pyotp.random_base32()
    otp_auth_url = pyotp.totp.TOTP(otp_base32).provisioning_uri(
        name=user.email.lower(), issuer_name=settings.OTP_AUTH_ISSUER_NAME
    )

    user.otp_auth_url = otp_auth_url
    user.otp_base32 = otp_base32
    user.save()

    return otp_base32, otp_auth_url


def verify_otp(user: User, otp_token: str):
    totp = pyotp.TOTP(user.otp_base32)
    if not totp.verify(otp_token):
        raise Exception(OTPErrors.VERIFICATION_TOKEN_INVALID.value)

    user.otp_enabled = True
    user.otp_verified = True
    user.save()


def validate_otp(user: User, otp_token: str):
    if not user.otp_verified:
        raise Exception(OTPErrors.OTP_NOT_VERIFIED.value)

    totp = pyotp.TOTP(user.otp_base32)
    if not totp.verify(otp_token, valid_window=1):
        raise Exception(OTPErrors.VERIFICATION_TOKEN_INVALID.value)


def disable_otp(user: User):
    user.otp_enabled = False
    user.otp_verified = False
    user.otp_base32 = ""
    user.otp_auth_url = ""

    user.save()
