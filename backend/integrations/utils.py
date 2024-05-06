from slack_sdk import WebClient

from .models import Bot, Agent


def save_bot(agent: Agent, oauth_response: dict, client: WebClient):
    installed_enterprise = oauth_response.get("enterprise") or {}
    is_enterprise_install = oauth_response.get("is_enterprise_install")
    installed_team = oauth_response.get("team") or {}
    installer = oauth_response.get("authed_user") or {}
    access_token = oauth_response.get("access_token")
    # NOTE: oauth.v2.access doesn't include bot_id in response
    bot_id = None
    enterprise_url = None
    if access_token is not None:
        auth_test = client.auth_test(token=access_token)
        bot_id = auth_test["bot_id"]
        print(f"Bot ID: {bot_id}")
        if is_enterprise_install is True:
            enterprise_url = auth_test.get("url")

    bot, _ = Bot.objects.get_or_create(
        agent=agent,
        user_id=installer.get("id"),
        app_id=oauth_response.get("app_id"),
        team_id=installed_team.get("id"),
        bot_id=bot_id,
        bot_user_id=oauth_response.get("bot_user_id"),
        defaults={
            "enterprise_id": installed_enterprise.get("id"),
            "enterprise_name": installed_enterprise.get("name"),
            "enterprise_url": enterprise_url,
            "team_name": installed_team.get("name"),
            "access_token": access_token,
            "bot_scopes": oauth_response.get("scope"),  # comma-separated string
            "user_token": installer.get("access_token"),
            "user_scopes": installer.get("scope"),  # comma-separated string
            "is_enterprise_install": is_enterprise_install,
            "token_type": oauth_response.get("token_type"),

        }
    )
    return bot