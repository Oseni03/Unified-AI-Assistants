import dramatiq

from agents.utils.utils import get_agent

from .models import ChatMessage


@dramatiq.actor
def chat_response(message_id):
    message = ChatMessage.objects.get(id=message_id)
    agent = get_agent(message.agent.integration, )