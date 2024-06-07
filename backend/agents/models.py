import hashlib
import os
from urllib.parse import urljoin

from django.db import models
from django.urls import reverse
from django.conf import settings

import requests

from accounts.models import User
from integrations.models import Integration
from common.models import AbstractBaseModel, ThirdParty


# Create your models here.
class Agent(AbstractBaseModel):
    name = models.CharField(max_length=100)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    thirdparty = models.CharField(max_length=50, choices=ThirdParty.choices)
    instance_url = models.URLField(null=True, blank=True, help_text="For Salesforce agent")
    state = models.CharField(
        max_length=255, default=hashlib.sha256(os.urandom(1024)).hexdigest()
    )
    integration = models.OneToOneField(
        Integration,
        on_delete=models.CASCADE,
        related_name="agent",
        null=True,
        blank=True,
    )

    def __str__(self):
        return str(self.name)

    @property
    def get_oauth_url(self) -> str:
        redirect_uri = settings.INTEGRATION_REDIRECT_URI
        if self.thirdparty == ThirdParty.GOOGLE_WORKSPACE:
            auth_url = settings.GOOGLE_AUTH_URI
            client_id = settings.GOOGLE_CLIENT_ID
            scope = " ".join(settings.GOOGLE_WORKSPACE_SCOPE)
        elif self.thirdparty == ThirdParty.ZOHO_WORKSPACE:
            auth_url = settings.ZOHO_AUTH_URI
            client_id = settings.ZOHO_CLIENT_ID
            scope = " ".join(settings.ZOHO_SCOPE)
        elif self.thirdparty == ThirdParty.SALESFORCE:
            auth_url = urljoin(self.agent.instance_url, "/services/oauth2/authorize")
            client_id = settings.SALESFORCE_CLIENT_ID
            scope = " ".join(settings.SALESFORCE_SCOPE)
        authorization_url = f"{auth_url}?response_type=code&client_id={client_id}&redirect_uri={redirect_uri}&access_type=offline&prompt=consent&scope={scope}"
        return authorization_url

    def handle_oauth_callback(self, code: str):
        redirect_uri = settings.INTEGRATION_REDIRECT_URI
        if self.thirdparty == ThirdParty.GOOGLE_WORKSPACE:
            token_url = settings.GOOGLE_TOKEN_URI
            client_id = settings.GOOGLE_CLIENT_ID
            client_secret = settings.GOOGLE_CLIENT_SECRET
        elif self.thirdparty == ThirdParty.ZOHO_WORKSPACE:
            token_url = settings.ZOHO_TOKEN_URI
            client_id = settings.ZOHO_CLIENT_ID
            client_secret = settings.ZOHO_CLIENT_SECRET
        elif self.thirdparty == ThirdParty.SALESFORCE:
            token_url = urljoin(self.agent.instance_url, "/services/oauth2/token")
            client_id = settings.SALESFORCE_CLIENT_ID
            client_secret = settings.SALESFORCE_CLIENT_SECRET

        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": client_id,
            "client_secret": client_secret,
        }
        response = requests.post(token_url, data=data)
        return response
