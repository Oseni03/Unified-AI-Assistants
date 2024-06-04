from django.shortcuts import get_object_or_404

from rest_framework import mixins, permissions, status
from rest_framework.viewsets import GenericViewSet
from rest_framework.response import Response
from rest_framework.decorators import action

from integrations.models import Agent
from feedbacks.serializers import FeedBackSerializer
from feedbacks.models import FeedBack

from .serializers import AgentSerializer, MessageSerializer
from .models import Message


# Create your views here.
class AgentViewSet(mixins.RetrieveModelMixin,
                   mixins.UpdateModelMixin,
                   mixins.DestroyModelMixin,
                   mixins.ListModelMixin,
                   GenericViewSet):
    """
    A viewset for viewing and editing user instances.
    """

    serializer_class = AgentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Agent.objects.filter(user=self.request.user)

    @action(detail=True, methods=["get", "post"], serializer_class=MessageSerializer)
    def chat(self, request, pk=None):
        if request.method == "GET":
            agent = self.get_object()
            messages = Message.objects.filter(agent=agent)
            serializer = MessageSerializer(messages, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        elif request.method == "POST":
            agent = self.get_object()
            serializer = MessageSerializer(data=request.data)
            if serializer.is_valid(raise_exception=True):
                serializer.save(agent=agent)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=["get", "post"], serializer_class=FeedBackSerializer)
    def feedbacks(self, request, pk=None):
        agent = self.get_object()
        if request.method == "GET":
            if pk:
                feedback = get_object_or_404(FeedBack, id=pk)
                serializer = FeedBackSerializer(feedback, many=False)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                feedbacks = FeedBack.objects.filter(agent=agent)
                serializer = FeedBackSerializer(feedbacks, many=True)
                return Response(serializer.data, status=status.HTTP_200_OK)
        elif request.method == "POST":
            serializer = FeedBackSerializer(data=request.data)
            if serializer.is_valid(raise_exception=True):
                serializer.save(agent=agent)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
