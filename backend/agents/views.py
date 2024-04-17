import requests
from django.conf import settings

from django.shortcuts import redirect
from rest_framework import status, generics, permissions
from rest_framework.response import Response

from .serializers import AgentSerializer
from .models import Agent
from .utils.google.utils import create_workspace_crew

from common.models import State, ThirdParty

# Create your views here.
class AgentAPIView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AgentSerializer

    def get_queryset(self):
        return Agent.objects.filter(user=self.request.user)


class OAuthAPIView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, thirdparty, **kwargs):
        state = State.issue()
        request.session["thirdparty"] = thirdparty # Add to the session

        if thirdparty == ThirdParty.GOOGLE:
            auth_url = f"""https://accounts.google.com/o/oauth2/v2/auth?
                response_type=code&
                client_id={settings.GOOGLE_CLIENT_ID}&
                scope={settings.GOOGLE_SCOPES}&
                redirect_uri={settings.GOOGLE_REDIRECT_URL}&
                state={state}&
                login_hint={request.user.email}"""
        return redirect(auth_url)


class OAuthCallBackAPIView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, **kwargs):
        # Ensure that the request is not a forgery and that the user sending
        # this connect request is the expected user.
        if  not State.consume(request.args.get('state', '')):
            return Response('Invalid state parameter.', status=status.HTTP_401_UNAUTHORIZED)
        
        code = request.args.get('code', '')
        thirdparty = request.session.get("thirdparty")
        if thirdparty == ThirdParty.GOOGLE:
            payload = {
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "grant_type": "autthorization_code"
            }

            response = requests.post("https://oauth2.googleapis.com/token", data=payload)

            access_token = response.get("access_token")
            id_token = response.get("id_token")

            crew = create_workspace_crew(access_token)

            agent = Agent(
                user=request.user,
                access_token=access_token,
                id_token=id_token,
                thirdparty=ThirdParty(thirdparty),
                data=crew.to_json()
            )
            agent.save()

        serializer = AgentSerializer(instance=agent)
        return Response(serializer.data, status=status.HTTP_201_CREATED)