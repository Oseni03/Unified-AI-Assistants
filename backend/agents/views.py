from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.decorators import action

from .models import Agent, FeedBack
from .serializers import AgentSerializer, FeedBackSerializer


# Create your views here.
class AgentListView(generics.ListAPIView):
    serializer_class = AgentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Agent.objects.filter(user=self.request.user)

    def list(self, request):
        # Note the use of `get_queryset()` instead of `self.queryset`
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class AgentDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AgentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Agent.objects.filter(user=self.request.user)

    # @action(
    #     methods=["post", "update", "delete"],
    #     detail=True,
    #     serializer_class=FeedBackSerializer,
    # )
    # def feedback(self, request, id=None, *args, **kwargs):
    #     if request.method == "POST":
    #         serializer = FeedBackSerializer(data=request.data)
    #         serializer.save(agent=self.get_object())
    #     elif request.method == "PUT":
    #         feedback = get_object_or_404(FeedBack, id=id)
    #         serializer = FeedBackSerializer(feedback, data=request.data)
    #         if serializer.is_valid():
    #             serializer.save()
    #     elif request.method == "DELETE":
    #         feedback = get_object_or_404(FeedBack, id=id).delete()
    #         return Response({}, status=status.HTTP_204_NO_CONTENT)
    #     return Response(serializer.data, status=status.HTTP_201_CREATED)
