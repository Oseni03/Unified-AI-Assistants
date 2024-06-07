import re
import json
import logging
import requests

from rest_framework import status
from rest_framework.response import Response

from slack_sdk import WebClient

from .tasks import agent_response
from .models import Bot, Agent, Integration


def save_bot(agent: Agent, oauth_response: dict, client: WebClient, integration: Integration):
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
        integration=integration,
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


def log_http_response(response):
    logging.info(f"Status: {response.status_code}")
    logging.info(f"Content-type: {response.headers.get('content-type')}")
    logging.info(f"Body: {response.text}")


def get_text_message_input(recipient, text):
    return json.dumps(
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "text",
            "text": {"preview_url": False, "body": text},
        }
    )


def generate_response(response):
    # Return text in uppercase
    return response.upper()


def send_message(data, access_token, version, phone_number_id):
    headers = {
        "Content-type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }

    url = f"https://graph.facebook.com/{version}/{phone_number_id}/messages"

    try:
        response = requests.post(
            url, data=data, headers=headers, timeout=10
        )  # 10 seconds timeout as an example
        response.raise_for_status()  # Raises an HTTPError if the HTTP request returned an unsuccessful status code
    except requests.Timeout:
        print("Timeout occurred while sending message")
        return Response(status=status.HTTP_408_REQUEST_TIMEOUT)
    except (
        requests.RequestException
    ) as e:  # This will catch any general request exception
        print(f"Request failed due to: {e}")
        return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        # Process the response as normal
        log_http_response(response)
        return response


def process_text_for_whatsapp(text):
    # Remove brackets
    pattern = r"\【.*?\】"
    # Substitute the pattern with an empty string
    text = re.sub(pattern, "", text).strip()

    # Pattern to find double asterisks including the word(s) in between
    pattern = r"\*\*(.*?)\*\*"

    # Replacement pattern with single asterisks
    replacement = r"*\1*"

    # Substitute occurrences of the pattern with the replacement
    whatsapp_style_text = re.sub(pattern, replacement, text)

    return whatsapp_style_text


def process_whatsapp_message(body):
    wa_id = body["entry"][0]["changes"][0]["value"]["contacts"][0]["wa_id"]
    name = body["entry"][0]["changes"][0]["value"]["contacts"][0]["profile"]["name"]
    # Lookup the stored bot token for this workspace
    try:
        bot = Bot.objects.get(
            whatsapp_id=wa_id,
            whatsapp_name=name,
        )
    except:
        print("Unknown whatsapp user-ID")
        return
    
    agent = bot.agent
    bot_token = bot.access_token
    if not bot_token:
        # The app may be uninstalled or be used in a shared channel
        print("Please install this app first!")
        return 

    message = body["entry"][0]["changes"][0]["value"]["messages"][0]
    message_body = message["text"]["body"]

    # TODO: implement custom function here
    response = generate_response(message_body)

    # OpenAI Integration
    # response = generate_response(message_body, wa_id, name)
    # response = process_text_for_whatsapp(response)

    data = get_text_message_input(bot.whatsapp_recipient_id, response)
    send_message(data)


def process_slack_message(data):
    event = data.get("event") or {}

    # print(event)

    # in the case where this app gets a request from an Enterprise Grid workspace
    # enterprise_id = data.get("enterprise_id")
    # The workspace's ID
    team_id = data.get("team_id")
    user_id = event.get("user")
    query = event.get("text")
    channel = event.get("channel")
    thread_ts = event.get("ts")

    # Lookup the stored bot token for this workspace
    try:
        bot = Bot.objects.get(
            user_id=user_id,
            team_id=team_id,
        )
    except:
        print("Unknown slack user-ID")
        return

    agent = bot.agent
    bot_token = bot.access_token
    if not bot_token:
        # The app may be uninstalled or be used in a shared channel
        print("Please install this app first!")
        return 

    client = WebClient(token=bot_token)
    bot_id = client.api_call("auth.test")["user_id"]

    if event.get("type") == "app_mention":
        blocks = event.get("blocks") or []
        elements = blocks[0].get("elements") or []
        user_id = elements[0].get("user_id")
        query = elements[1].get("text")
    else:
        user_id = event.get("user")
        query = event.get("text")

    # Ignore bot's own message
    if user_id == bot_id:
        print("user-ID and bot-ID is the same")
        return

    # Post an initial message
    # result = client.chat_postMessage(
    #     channel=channel, text=":mag: Searching...", thread_ts=thread_ts
    # )
    # thread_ts = result.get("ts")

    print("About to run task")
    print(f"""agent_id: {agent.id}
            channel: {channel}
            bot_token: {bot_token}
            query: {query}
            thread_ts: {thread_ts}""")
    # send_agent_response.delay(agent.id, channel, thread_ts, bot_token, query)
    agent_response.send(
        bot_id=bot.id,
        channel=channel,
        thread_ts=thread_ts,
        bot_token=bot_token,
        query=query,
        user_id=user_id,
    )


def is_valid_whatsapp_message(body):
    """
    Check if the incoming webhook event has a valid WhatsApp message structure.
    """
    return (
        body.get("object")
        and body.get("entry")
        and body["entry"][0].get("changes")
        and body["entry"][0]["changes"][0].get("value")
        and body["entry"][0]["changes"][0]["value"].get("messages")
        and body["entry"][0]["changes"][0]["value"]["messages"][0]
    )


def is_valid_slack_message(data):
    """
    Check if the incoming webhook event has a valid WhatsApp message structure.
    """
    return (
        data.get("type") == "event_callback"
        and data["event"].get("user")
        and data["event"].get("channel")
    )
