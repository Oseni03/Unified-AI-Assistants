from django.urls import reverse
import google_auth_oauthlib
import google.oauth2.credentials

from typing import Any, Dict, Optional

from django.conf import settings
from django.db import models

from slack_sdk.oauth.installation_store.models.bot import Bot as SlackBot
from slack_sdk.oauth import AuthorizeUrlGenerator
from slack_sdk import WebClient

from common.models import AbstractBaseModel, ThirdParty


# Create your models here.
class Integration(AbstractBaseModel):
    thirdparty = models.CharField(
        max_length=50, unique=True, choices=ThirdParty.choices
    )
    is_chat_app = models.BooleanField(
        help_text="Is it a messaging app integration or other thirdparty integration"
    )
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return str(self.thirdparty.title)

    def get_absolute_url(self):
        if not self.is_chat_app:
            return reverse(
                "integrations:agent-install", kwargs={"thirdparty": self.thirdparty}
            )

    def get_oauth_url(self, state: str, user_email: str) -> str:
        if (
            self.thirdparty == ThirdParty.GMAIL
            or self.thirdparty == ThirdParty.GOOGLE_CALENDER
            or self.thirdparty == ThirdParty.GOOGLE_DOCUMENT
            or self.thirdparty == ThirdParty.GOOGLE_DRIVE
            or self.thirdparty == ThirdParty.GOOGLE_SHEET
            or self.thirdparty == ThirdParty.GOOGLE_FORM
        ):
            flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
                settings.DEFAULT_CLIENT_SECRETS_FILE,
                scopes=self.scopes,
            )
            flow.redirect_uri = settings.INTEGRATION_REDIRECT_URI
            auth_url, _ = flow.authorization_url(
                access_type="offline",
                include_granted_scopes="true",
                state=state,
                login_hint=user_email,
                prompt="consent",
            )
        elif self.thirdparty == ThirdParty.SLACK:
            # Build https://slack.com/oauth/v2/authorize with sufficient query parameters
            authorize_url_generator = AuthorizeUrlGenerator(
                client_id=settings.SLACK_CLIENT_ID,
                scopes=self.scopes,  # settings.SLACK_SCOPES,
                # user_scopes=["search:read"],
                redirect_uri=settings.INTEGRATION_REDIRECT_URI,
            )
            auth_url = authorize_url_generator.generate(state)
        return auth_url

    def handle_oauth_callback(self, state: str, code: str, client: WebClient = None):
        if (
            self.thirdparty == ThirdParty.GMAIL
            or self.thirdparty == ThirdParty.GOOGLE_CALENDER
            or self.thirdparty == ThirdParty.GOOGLE_DOCUMENT
            or self.thirdparty == ThirdParty.GOOGLE_DRIVE
            or self.thirdparty == ThirdParty.GOOGLE_SHEET
            or self.thirdparty == ThirdParty.GOOGLE_FORM
        ):
            flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
                settings.DEFAULT_CLIENT_SECRETS_FILE, scopes=self.scopes, state=state
            )
            redirect_uri = settings.INTEGRATION_REDIRECT_URI
            print(f"Redirect URI: {redirect_uri}")
            flow.redirect_uri = redirect_uri
            flow.fetch_token(code=code)
            credentials = flow.credentials
            return credentials

        elif self.thirdparty == ThirdParty.SLACK:  # no prepared token needed for this
            # Complete the installation by calling oauth.v2.access API method
            oauth_response = client.oauth_v2_access(
                client_id=settings.SLACK_CLIENT_ID,
                client_secret=settings.SLACK_CLIENT_SECRET,
                redirect_uri=settings.INTEGRATION_REDIRECT_URI,
                code=code,
            )
            return oauth_response

    @property
    def scopes(self):
        if self.thirdparty == ThirdParty.GMAIL:
            return settings.GOOGLE_GMAIL_SCOPES
        elif self.thirdparty == ThirdParty.GOOGLE_CALENDER:
            return settings.GOOGLE_CALENDER_SCOPES
        elif self.thirdparty == ThirdParty.GOOGLE_DOCUMENT:
            return settings.GOOGLE_DOCUMENT_SCOPES
        elif self.thirdparty == ThirdParty.GOOGLE_DRIVE:
            return settings.GOOGLE_DRIVE_SCOPES
        elif self.thirdparty == ThirdParty.GOOGLE_SHEET:
            return settings.GOOGLE_SHEET_SCOPES
        elif self.thirdparty == ThirdParty.GOOGLE_FORM:
            return settings.GOOGLE_FORM_SCOPES
        elif self.thirdparty == ThirdParty.SLACK:
            return settings.SLACK_SCOPES
        return []


class Agent(AbstractBaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="agents",
        null=True,
    )
    name = models.CharField(max_length=255, default="AI assistant")
    access_token = models.CharField(max_length=255)
    refresh_token = models.CharField(max_length=255, null=True)
    token_uri = models.CharField(max_length=255, null=True)
    id_token = models.CharField(max_length=255, null=True)
    integration = models.ForeignKey(
        Integration, on_delete=models.CASCADE, related_name="agents"
    )
    is_public = models.BooleanField(default=False)
    scopes_text = models.TextField(null=True)
    data = models.JSONField(null=True)  # agent.json() or agent.dict()

    def __str__(self):
        return str(self.name)

    @property
    def credentials(self):
        if (
            self.integration.thirdparty == ThirdParty.GMAIL
            or self.integration.thirdparty == ThirdParty.GOOGLE_CALENDER
        ):
            credentials = google.oauth2.credentials.Credentials(
                token=self.access_token,
                refresh_token=self.refresh_token,
                token_uri=self.token_uri,
                client_id=settings.GOOGLE_CLIENT_ID,
                client_secret=settings.GOOGLE_CLIENT_SECRET,
                scopes=self.scopes,
            )
            return credentials

        return None

    @property
    def scopes(self):
        scopes = [scope.strip() for scope in self.scopes_text.split(",")]
        return scopes


class Bot(AbstractBaseModel):
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name="bots")
    app_id = models.CharField(max_length=255, null=True)
    user_id = models.CharField(max_length=255)
    enterprise_id = models.CharField(max_length=255, null=True)
    enterprise_name = models.CharField(max_length=255, null=True)
    enterprise_url = models.CharField(max_length=255, null=True)
    team_id = models.CharField(max_length=255, null=True)
    team_name = models.CharField(max_length=255, null=True)
    access_token = models.CharField(max_length=255, null=True)
    bot_id = models.CharField(max_length=255, null=True)
    bot_user_id = models.CharField(max_length=255, null=True)
    bot_scopes = models.CharField(
        max_length=500, null=True, help_text="Comma separated string"
    )
    bot_refresh_token = models.CharField(
        max_length=255, null=True, help_text="Only when token rotation is enabled"
    )
    access_token_expires_in = models.DateTimeField(null=True)
    user_token = models.CharField(max_length=255, null=True)
    user_scopes = models.CharField(
        max_length=500, null=True, help_text="Comma separated string"
    )
    user_refresh_token = models.CharField(
        max_length=255, null=True, help_text="Only when token rotation is enabled"
    )
    user_token_expires_at = models.DateTimeField(null=True)
    incoming_webhook_url = models.CharField(max_length=255, null=True)
    incoming_webhook_channel = models.CharField(max_length=255, null=True)
    incoming_webhook_channel_id = models.CharField(max_length=255, null=True)
    incoming_webhook_configuration_url = models.CharField(max_length=255, null=True)
    is_enterprise_install = models.BooleanField(default=False)
    token_type = models.CharField(max_length=255, null=True)
    installed_at = models.DateTimeField(auto_now=True)
    custom_values = models.JSONField(null=True)

    class Meta:
        models.UniqueConstraint(
            fields=["app_id", "user_id", "team_id"], name="unique_user_team_app"
        )

    def to_bot(self) -> SlackBot:
        return SlackBot(
            app_id=self.app_id,
            enterprise_id=self.enterprise_id,
            enterprise_name=self.enterprise_name,
            team_id=self.team_id,
            team_name=self.team_name,
            bot_token=self.access_token,
            bot_id=self.bot_id,
            bot_user_id=self.bot_user_id,
            bot_scopes=self.bot_scopes,
            bot_refresh_token=self.bot_refresh_token,
            bot_token_expires_at=self.access_token_expires_in,
            is_enterprise_install=self.is_enterprise_install,
            installed_at=self.installed_at,
            custom_values=self.custom_values,
        )

    def set_custom_value(self, name: str, value: Any):
        self.custom_values[name] = value

    def get_custom_value(self, name: str) -> Optional[Any]:
        return self.custom_values.get(name)

    def to_dict(self) -> Dict[str, Any]:
        standard_values = {
            "app_id": self.app_id,
            "enterprise_id": self.enterprise_id,
            "enterprise_name": self.enterprise_name,
            "enterprise_url": self.enterprise_url,
            "team_id": self.team_id,
            "team_name": self.team_name,
            "access_token": self.access_token,
            "bot_id": self.bot_id,
            "bot_user_id": self.bot_user_id,
            "bot_scopes": ",".join(self.bot_scopes) if self.bot_scopes else None,
            "bot_refresh_token": self.bot_refresh_token,
            "access_token_expires_in": (
                self.access_token_expires_in
                if self.access_token_expires_in is not None
                else None
            ),
            "user_id": self.user_id,
            "user_token": self.user_token,
            "user_scopes": self.user_scopes.split(" , ") if self.user_scopes else None,
            "user_refresh_token": self.user_refresh_token,
            "user_token_expires_at": (
                self.user_token_expires_at
                if self.user_token_expires_at is not None
                else None
            ),
            "incoming_webhook_url": self.incoming_webhook_url,
            "incoming_webhook_channel": self.incoming_webhook_channel,
            "incoming_webhook_channel_id": self.incoming_webhook_channel_id,
            "incoming_webhook_configuration_url": self.incoming_webhook_configuration_url,
            "is_enterprise_install": self.is_enterprise_install,
            "token_type": self.token_type,
            "installed_at": self.installed_at,
        }
        # prioritize standard_values over custom_values
        # when the same keys exist in both
        return {**self.custom_values, **standard_values}
