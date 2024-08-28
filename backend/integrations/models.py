import requests
from datetime import datetime, timedelta

from django.conf import settings
from django.db import models

from common.models import AbstractBaseModel, ThirdParty
from accounts.models import User


# Create your models here.
class Integration(AbstractBaseModel):
    thirdparty = models.CharField(max_length=25, choices=ThirdParty.choices)
    is_chat_app = models.BooleanField(default=False)
    is_workspace = models.BooleanField(default=False)
    access_token = models.CharField(max_length=255)
    refresh_token = models.CharField(max_length=255)
    webhook_url = models.CharField(max_length=255, null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    def refresh_token(self):
        if self.expires_at and datetime.now() > self.expires_at:
            if self.thirdparty == ThirdParty.GOOGLE_WORKSPACE:
                token_url = settings.GOOGLE_TOKEN_URI
                client_id = settings.GOOGLE_CLIENT_ID
                client_secret = settings.GOOGLE_CLIENT_SECRET
                
            data = {
                'grant_type': 'refresh_token',
                'refresh_token': self.refresh_token,
                'client_id': client_id,
                'client_secret': client_secret,
            }
            response = requests.post(token_url, data=data)
            if response.status_code == 200:
                tokens = response.json()
                self.access_token = tokens['access_token']
                self.refresh_token = tokens.get('refresh_token')
                self.expires_at = datetime.now() + timedelta(seconds=tokens['expires_in'])
                self.save()
            else:
                raise Exception("Failed to refresh token")

    @property
    def scopes(self):
        if self.thirdparty == ThirdParty.GOOGLE_WORKSPACE:
            return settings.GOOGLE_WORKSPACE_SCOPES
        return []
