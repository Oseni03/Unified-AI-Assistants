from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from uuid import uuid4
from django.conf import settings
from django.db import models

from slack_sdk.oauth.installation_store.models.bot import Bot

from agents.models import Agent
from common.models import AbstractBaseModel

# Create your models here.
class Bot(AbstractBaseModel):
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name="slackbots")
    app_id = models.CharField(max_length=255, null=True)
    user_id = models.CharField(max_length=255)
    enterprise_id = models.CharField(max_length=255, null=True)
    enterprise_name = models.CharField(max_length=255, null=True)
    enterprise_url = models.CharField(max_length=255, null=True)
    team_id = models.CharField(max_length=255, null=True)
    team_name = models.CharField(max_length=255, null=True)
    bot_token = models.CharField(max_length=255, null=True)
    bot_id = models.CharField(max_length=255, null=True)
    bot_user_id = models.CharField(max_length=255, null=True)
    bot_scopes = models.CharField(max_length=500, null=True, help_text="Comma separated string")
    bot_refresh_token = models.CharField(max_length=255, null=True, help_text="Only when token rotation is enabled")
    bot_token_expires_at = models.DateTimeField(null=True)
    user_token = models.CharField(max_length=255, null=True)
    user_scopes = models.CharField(max_length=500, null=True, help_text="Comma separated string")
    user_refresh_token = models.CharField(max_length=255, null=True, help_text="Only when token rotation is enabled")
    user_token_expires_at = models.DateTimeField(null=True)
    incoming_webhook_url = models.CharField(max_length=255, null=True)
    incoming_webhook_channel = models.CharField(max_length=255, null=True)
    incoming_webhook_channel_id = models.CharField(max_length=255, null=True)
    incoming_webhook_configuration_url = models.CharField(max_length=255, null=True)
    is_enterprise_install = models.BooleanField(default=False)
    token_type = models.CharField(max_length=255, null=True)
    installed_at = models.DateTimeField()
    custom_values = models.JSONField(null=True)

    def __init__(
        self,
        *,
        app_id,
        # org / workspace
        enterprise_id,
        enterprise_name,
        enterprise_url,
        team_id,
        team_name,
        # bot
        bot_token,
        bot_id,
        bot_user_id,
        bot_scopes,
        bot_refresh_token,  # only when token rotation is enabled
        # only when token rotation is enabled
        bot_token_expires_in,
        # only for duplicating this object
        # only when token rotation is enabled
        bot_token_expires_at,
        # installer
        user_id: str,
        user_token,
        user_scopes,
        user_refresh_token,  # only when token rotation is enabled
        # only when token rotation is enabled
        user_token_expires_at,
        # incoming webhook
        incoming_webhook_url,
        incoming_webhook_channel,
        incoming_webhook_channel_id,
        incoming_webhook_configuration_url,
        # org app
        is_enterprise_install,
        token_type,
        # timestamps
        # The expected value type is float but the internals handle other types too
        # for str values, we supports only ISO datetime format.
        installed_at,
        # custom values
        custom_values,
    ):
        self.app_id = app_id
        self.enterprise_id = enterprise_id
        self.enterprise_name = enterprise_name
        self.enterprise_url = enterprise_url
        self.team_id = team_id
        self.team_name = team_name
        self.bot_token = bot_token
        self.bot_id = bot_id
        self.bot_user_id = bot_user_id
        if isinstance(bot_scopes, list):
            self.bot_scopes = " , ".join(bot_scopes)
            # self.bot_scopes = bot_scopes.split(",") if len(bot_scopes) > 0 else []
        else:
            self.bot_scopes = bot_scopes
        self.bot_refresh_token = bot_refresh_token
        self.bot_token_expires_at = bot_token_expires_at

        self.user_id = user_id
        self.user_token = user_token
        if isinstance(user_scopes, str):
            self.user_scopes = user_scopes.split(",") if len(user_scopes) > 0 else []
        else:
            self.user_scopes = user_scopes
        self.user_refresh_token = user_refresh_token
        
        self.user_token_expires_at = user_token_expires_at

        self.incoming_webhook_url = incoming_webhook_url
        self.incoming_webhook_channel = incoming_webhook_channel
        self.incoming_webhook_channel_id = incoming_webhook_channel_id
        self.incoming_webhook_configuration_url = incoming_webhook_configuration_url

        self.is_enterprise_install = is_enterprise_install or False
        self.token_type = token_type

        if installed_at is None:
            self.installed_at = datetime.now().timestamp()
        else:
            self.installed_at = installed_at

        self.custom_values = custom_values if custom_values is not None else {}

    def to_bot(self) -> Bot:
        return Bot(
            app_id=self.app_id,
            enterprise_id=self.enterprise_id,
            enterprise_name=self.enterprise_name,
            team_id=self.team_id,
            team_name=self.team_name,
            bot_token=self.bot_token,
            bot_id=self.bot_id,
            bot_user_id=self.bot_user_id,
            bot_scopes=self.bot_scopes,
            bot_refresh_token=self.bot_refresh_token,
            bot_token_expires_at=self.bot_token_expires_at,
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
            "bot_token": self.bot_token,
            "bot_id": self.bot_id,
            "bot_user_id": self.bot_user_id,
            "bot_scopes": ",".join(self.bot_scopes) if self.bot_scopes else None,
            "bot_refresh_token": self.bot_refresh_token,
            "bot_token_expires_at": self.bot_token_expires_at
            if self.bot_token_expires_at is not None
            else None,
            "user_id": self.user_id,
            "user_token": self.user_token,
            "user_scopes": self.user_scopes.split(" , ") if self.user_scopes else None,
            "user_refresh_token": self.user_refresh_token,
            "user_token_expires_at": self.user_token_expires_at
            if self.user_token_expires_at is not None
            else None,
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


class State(AbstractBaseModel):
    is_used = models.BooleanField(default=False)

    @classmethod
    def issue():
        return State().id
    
    @classmethod
    def consume(state: uuid4):
        try:
            state = State.objects.get(id=state, is_used=False)
            state.is_used = True
            state.save()

            expiration = state.created_at + timedelta(seconds=settings.SLACK_STATE_EXPIRATION_SECONDS)
            still_valid: bool = datetime.now() < expiration
            return still_valid
        except:
            return False