from django.conf import settings
from django.http import HttpRequest
from django.shortcuts import redirect, get_object_or_404

from rest_framework import status, generics, permissions
from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action

from agents.utils.google.utils import google_oauth, google_oauth_callback

from .models import Agent, FeedBack
from .serializers import AgentSerializer, FeedBackSerializer
from .utils.google.utils import credentials_to_dict, get_agent
from common.models import State, ThirdParty

# Create your views here.
class AgentViewset(viewsets.ModelViewSet):
    serializer_class = AgentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Agent.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        return serializer.save(user=self.request.user)

    @action(methods=["post", "update", "delete"], detail=True, serializer_class=FeedBackSerializer)
    def feedback(self, request, id=None, *args, **kwargs):
        if request.method == "POST":
            serializer = FeedBackSerializer(data=request.data)
            serializer.save(agent=self.get_object())
        elif request.method == "PUT":
            feedback = get_object_or_404(FeedBack, id=id)
            serializer = FeedBackSerializer(feedback, data=request.data)
            if serializer.is_valid():
                serializer.save()
        elif request.method == "DELETE":
            feedback = get_object_or_404(FeedBack, id=id).delete()
            return Response({}, status=status.HTTP_204_NO_CONTENT)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class OAuthAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, thirdparty, **kwargs):
        gen_state = State().issue(thirdparty)
        request.session["thirdparty"] = thirdparty # Add to the session
        request.session["state"] = gen_state # Add to the session

        if thirdparty == ThirdParty.GMAIL:
            auth_url, state = google_oauth(thirdparty, gen_state, request.user.email)
        elif thirdparty == ThirdParty.GOOGLE_CALENDER:
            auth_url, state = google_oauth(thirdparty, gen_state, request.user.email)
        print(auth_url)
        return redirect(auth_url)


class OAuthCallBackAPIView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AgentSerializer

    def get(self, request: HttpRequest, **kwargs):
        # Ensure that the request is not a forgery and that the user sending
        # this connect request is the expected user.
        state = request.GET.get('state', '')
        gen_state = request.session.get("state")
        print(f"State: {state}")
        if not (state == gen_state):
            return Response('Invalid state parameter.', status=status.HTTP_401_UNAUTHORIZED)
        
        State.consume(state)
        
        code = request.GET.get('code', '')
        print(f"Code: {code}")
        thirdparty = request.session.get("thirdparty")
        print(f"Thirdparty: {thirdparty}")
        
        if thirdparty == ThirdParty.GMAIL:
            credentials = google_oauth_callback(thirdparty, state, code)
            print(credentials_to_dict(credentials))
            llm_agent = get_agent(thirdparty, credentials)
            agent_json = llm_agent.json()
            print(agent_json)
            agent = Agent(
                user=request.user,
                access_token=credentials.token,
                refresh_token=credentials.refresh_token,
                token_uri=credentials.token_uri,
                thirdparty=ThirdParty(thirdparty),
                data=agent_json
            )
            agent.save()

        serializer = self.get_serializer(instance=agent)
        return Response(serializer.data, status=status.HTTP_201_CREATED)