from datetime import datetime, timedelta
from django.shortcuts import redirect
from django.utils import timezone

from rest_framework import mixins, permissions, status
from rest_framework.viewsets import GenericViewSet
from rest_framework.response import Response
from rest_framework.decorators import action

from integrations.models import Integration
from feedbacks.serializers import TicketSerializer
from feedbacks.models import Ticket
from chat.models import ChatMessage
from chat.serializers import ChatMessageSerializer

from .models import Agent
from .serializers import AgentSerializer


# Create your views here.
class AgentViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    """A View for creating, retrieving, updating and deleting agent.
    After a successful agent ceation from the frontend, the frontend then call the authorize url with the newly ceated agent ID
    """

    serializer_class = AgentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Agent.objects.filter(user=self.request.user)

    @action(detail=True, methods=["get"])
    def authorize(self, request, pk=None):
        agent = self.get_object()
        authorization_url = agent.get_oauth_url
        request.session["agent_id"] = agent.id
        return redirect(authorization_url)

    @action(detail=False, methods=["get"], serializer_class=None)
    def callback(self, request, pk=None):
        agent_id = request.session.get("agent_id")
        agent = Agent.objects.get(id=agent_id)

        code = request.GET.get("code")
        oauth_response = agent.handle_oauth_callback(code)
        print(oauth_response.json())
        if oauth_response.status_code == 200:
            try:
                response = oauth_response.json()
                integration = Integration.objects.create(
                    thirdpary=agent.thirdparty,
                    access_token=response.get("access_token"),
                    refresh_token=response.get("refresh_token"),
                    expires_at=timezone.now() + timedelta(seconds=int(response.get("expires_in", None) or response.get("issued_at"))),
                    user=request.user,
                )
                agent.integration = integration
                agent.save()
                return Response(
                    {"status": "Authorization successful"}, status=status.HTTP_200_OK
                )
            except Exception as error:
                return Response(
                    {"error": f"{error}"}, status=status.HTTP_400_BAD_REQUEST
                )
        else:
            return Response(
                {"error": "Authorization failed"}, status=status.HTTP_400_BAD_REQUEST
            )

    @action(
        detail=True, methods=["get", "post"], serializer_class=ChatMessageSerializer
    )
    def chat(self, request, pk=None):
        agent = self.get_object()
        if request.method == "GET":
            messages = ChatMessage.objects.filter(agent=agent)
            serializer = ChatMessageSerializer(messages, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        elif request.method == "POST":
            data = request.data
            chat_message = ChatMessage.objects.create(
                agent=agent,
                message=data["message"]
            )
            return Response(ChatMessageSerializer(chat_message).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], serializer_class=TicketSerializer)
    def feedbacks(self, request, pk=None):
        agent = self.get_object()
        serializer = TicketSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.save(agent=agent)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def set_webhook(self, request, pk=None):
        integration = self.get_object().integration
        webhook_url = request.data.get('webhook_url')
        integration.webhook_url = webhook_url
        integration.save()
        return Response({'status': 'Webhook URL set'}, status=status.HTTP_200_OK)
