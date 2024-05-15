from celery import shared_task
from celery.utils.log import get_task_logger
from slack_sdk import WebClient

from agents.utils.utils import get_agent
from common.models import ThirdParty
from integrations.models import Agent

logger = get_task_logger(__name__)


@shared_task
def add(a, b):
    return a + b


@shared_task
def agent_response(agent_id, channel, thread_ts, bot_token, query, user_id=None):
    try:
        logger.info("Creating agent")
        agent = Agent.objects.get(id=agent_id)
        agent_executor = get_agent(agent.integration, agent.credentials)
        
        response = agent_executor.invoke({"input": query})

        logger.info(response)

        output_text = response[
            "output"
        ]  # Adjust according to your actual response structure

        if user_id:
            output_text = f"<@{user_id}> {output_text}"

        if agent.integration == ThirdParty.SLACK:
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
        logger.info("Message send successfully")
        return response
    except Exception as e:
        raise e