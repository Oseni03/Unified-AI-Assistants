from django.conf import settings

from django.shortcuts import redirect, get_object_or_404
from rest_framework import status, generics, permissions
from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action

from agents.utils.google.utils import google_oauth, google_oauth_callback

from .models import Agent, FeedBack
from .serializers import AgentSerializer, FeedBackSerializer
from .utils.google.utils import get_agent
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
        gen_state = State.issue()
        request.session["thirdparty"] = thirdparty # Add to the session

        if thirdparty == ThirdParty.GMAIL:
            auth_url, state = google_oauth(thirdparty, gen_state, request.user.email)
            request.session["state"] = state
        elif thirdparty == ThirdParty.GOOGLE_CALENDER:
            auth_url, state = google_oauth(thirdparty, gen_state, request.user.email)
            request.session["state"] = state
        return redirect(auth_url)


class OAuthCallBackAPIView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AgentSerializer

    def get(self, request, **kwargs):
        # Ensure that the request is not a forgery and that the user sending
        # this connect request is the expected user.
        state = request.args.get('state', '')
        if  not State.consume(state):
            return Response('Invalid state parameter.', status=status.HTTP_401_UNAUTHORIZED)
        
        code = request.args.get('code', '')
        thirdparty = request.session.get("thirdparty")
        if thirdparty == ThirdParty.GMAIL:
            credentials = google_oauth_callback(thirdparty, state)
            print(credentials)
            llm_agent = get_agent(thirdparty)
            agent = Agent(
                user=request.user,
                access_token=credentials.token,
                refresh_token=credentials.refresh_token,
                token_uri=credentials.token_uri,
                thirdparty=ThirdParty(thirdparty),
                data=llm_agent.json()
            )
            agent.save()

            # payload = {
            #     "code": code,
            #     "client_id": settings.GOOGLE_CLIENT_ID,
            #     "client_secret": settings.GOOGLE_CLIENT_SECRET,
            #     "redirect_uri": settings.AGENT_REDIRECT_URI,
            #     "grant_type": "autthorization_code"
            # }

            # response = requests.post("https://oauth2.googleapis.com/token", data=payload)

            # access_token = response.get("access_token")
            # id_token = response.get("id_token")

        serializer = self.get_serializer(instance=agent)
        return Response(serializer.data, status=status.HTTP_201_CREATED)