import dramatiq
from slack_sdk import WebClient

from agents.utils.utils import get_agent
from agents.models import Message
from common.models import ThirdParty
from .models import Agent, Bot


@dramatiq.actor
def add(a, b):
    return a + b


@dramatiq.actor
def agent_response(bot_id, channel, thread_ts, bot_token, query, user_id=None):
    try:
        print("Creating agent")
        bot = Bot.objects.select_related(
            "agent__integration", "bot__agent__integration"
        ).get(id=bot_id)
        print(bot.integration.thirdparty)
        agent_executor = get_agent(bot.agent.integration, bot.agent.credentials)

        messages = Message.objects.all()[:5]
        message_list = []

        for msg in messages:
            if msg.is_ai:
                message_list.append(("ai", msg.text))
            else:
                message_list.append(("user", msg.text))

        message_list.append(("user", query))
        print(message_list)

        response = agent_executor.invoke({"input": message_list})

        print(response)

        output_text = response[
            "output"
        ]  # Adjust according to your actual response structure

        if user_id:
            output_text = f"<@{user_id}> {output_text}"

        if bot.integration.thirdparty == ThirdParty.SLACK:
            # Update the initial message with the response and use mrkdown block section to return the response in Slack markdown format
            # client.chat_update(
            client = WebClient(token=bot_token)
            client.chat_postMessage(
                channel=channel,
                ts=thread_ts,
                text=output_text,
                blocks=[
                    {"type": "section", "text": {"type": "mrkdwn", "text": output_text}}
                ],
            )
        print("Message sent successfully")
        return response
    except Exception as e:
        raise e
