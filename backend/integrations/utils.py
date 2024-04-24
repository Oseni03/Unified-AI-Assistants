from django.shortcuts import get_object_or_404
from slack_sdk import WebClient

from agents.models import Agent
from accounts.models import User

from .models import Bot


def save_bot(agent: Agent, oauth_response: dict, client: WebClient):
    installed_enterprise = oauth_response.get("enterprise") or {}
    is_enterprise_install = oauth_response.get("is_enterprise_install")
    installed_team = oauth_response.get("team") or {}
    installer = oauth_response.get("authed_user") or {}
    incoming_webhook = oauth_response.get("incoming_webhook") or {}
    bot_token = oauth_response.get("access_token")
    # NOTE: oauth.v2.access doesn't include bot_id in response
    bot_id = None
    enterprise_url = None
    if bot_token is not None:
        auth_test = client.auth_test(token=bot_token)
        bot_id = auth_test["bot_id"]
        if is_enterprise_install is True:
            enterprise_url = auth_test.get("url")

    bot = Bot(
        agent=agent,
        app_id=oauth_response.get("app_id"),
        enterprise_id=installed_enterprise.get("id"),
        enterprise_name=installed_enterprise.get("name"),
        enterprise_url=enterprise_url,
        team_id=installed_team.get("id"),
        team_name=installed_team.get("name"),
        bot_token=bot_token,
        bot_id=bot_id,
        bot_user_id=oauth_response.get("bot_user_id"),
        bot_scopes=oauth_response.get("scope"),  # comma-separated string
        user_id=installer.get("id"),
        user_token=installer.get("access_token"),
        user_scopes=installer.get("scope"),  # comma-separated string
        incoming_webhook_url=incoming_webhook.get("url"),
        incoming_webhook_channel=incoming_webhook.get("channel"),
        incoming_webhook_channel_id=incoming_webhook.get("channel_id"),
        incoming_webhook_configuration_url=incoming_webhook.get("configuration_url"),
        is_enterprise_install=is_enterprise_install,
        token_type=oauth_response.get("token_type"),
    )

    # Store the bot
    return bot.save()


def fetch_response(query: str, bot_id, user: User):
    bot = get_object_or_404(Bot, bot_id=bot_id, user=user)
    response = bot.agent.invoke(query)
    return response