# from django.db.models.signals import post_save
# from django.dispatch import receiver

# from .models import Agent
# from .utils.google.utils import get_agent


# @receiver(post_save, sender=Agent)
# def create_agent(sender, created, instance):
#     if created:
#         agent = get_agent(instance.thirdparty, instance.credentials)
#         agent_json = agent.json()
#         print(agent_json)
#         instance.data = agent_json
#         instance.save()