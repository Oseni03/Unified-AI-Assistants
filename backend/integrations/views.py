from django.conf import settings
from django.shortcuts import get_object_or_404, redirect
from django.http import HttpRequest

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics, permissions

from slack_sdk.errors import SlackApiError
from slack_sdk.signature import SignatureVerifier
from slack_sdk import WebClient

from agents.utils.utils import credentials_to_dict
from agents.serializers import AgentSerializer
from common.models import State

from .utils import save_bot
from .models import Bot, Integration, Agent
from .serializers import BotSerializer, IntegrationSerializer
from .utils import is_valid_whatsapp_message, process_whatsapp_message, is_valid_slack_message, process_slack_message


# Create your views here.
class IntegrationListView(generics.ListAPIView):
    queryset = Integration.objects.filter(is_active=True)
    serializer_class = IntegrationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['is_chat_app']


class OAUTHView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request: HttpRequest, thirdparty: str, agent_id=None, **kwargs):
        if agent_id:
            request.session["agent_id"] = agent_id
        # Generate a random value and store it on the server-side
        state = State().issue(thirdparty)
        print(state)
        print(thirdparty)
        request.session["thirdparty"] = thirdparty  # Add to the session
        request.session["state"] = state  # Add to the session

        integration = Integration.objects.get(thirdparty=thirdparty)
        auth_url = integration.get_oauth_url(state=state, user_email=request.user.email)
        print(auth_url)
        return redirect(auth_url)


class OAUTHCallbackView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request: HttpRequest, **kwargs):
        try:
            # Ensure that the request is not a forgery and that the user sending
            # this connect request is the expected user.
            state = request.GET.get("state", "")
            code = request.GET.get("code", "")

            gen_state = request.session.get("state")
            thirdparty = request.session.get("thirdparty")
            agent_id = request.session.get("agent_id", "")

            print(
                f"State: {state}\nCode: {code}\nThirdparty: {thirdparty}\nAgent-ID: {agent_id}"
            )

            if not (state == gen_state):
                return Response(
                    "Invalid state parameter.", status=status.HTTP_401_UNAUTHORIZED
                )

            State.consume(state)

            integration = Integration.objects.get(thirdparty=thirdparty)
            if integration.is_chat_app:
                agent_id = request.session.get("agent_id")
                client = WebClient()
                oauth_response = integration.handle_oauth_callback(
                    state, code, client=client
                )

                print(oauth_response)

                agent = get_object_or_404(Agent, id=agent_id)
                bot = save_bot(agent, oauth_response, client, integration)

                serializer = BotSerializer(instance=bot)

                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                credentials = integration.handle_oauth_callback(state, code)
                print(credentials)

                print(credentials_to_dict(credentials))
                agent = Agent(
                    user=request.user,
                    access_token=credentials.token,
                    refresh_token=credentials.refresh_token,
                    token_uri=credentials.token_uri,
                    integration=integration,
                    scopes_text=", ".join(credentials.scopes),
                )
                agent.save()

                serializer = AgentSerializer(instance=agent)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as error:
            error = request.GET.get("error", "")
            if error == "access_denied":
                return Response(
                    {"message": "Access denied!"}, status=status.HTTP_204_NO_CONTENT
                )
            elif error == "admin_policy_enforced":
                return Response(
                    {
                        "message": "The Google Account is unable to authorize one or more scopes requested due to the policies of their Google Workspace administrator."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            else:
                return Response(
                    {"message": f"Invalid request with error: {error}."},
                    status=status.HTTP_400_BAD_REQUEST,
                )


signature_verifier = SignatureVerifier(signing_secret=settings.SLACK_SIGNING_SECRET)


class EventView(APIView):
    """Token Lookup"""

    permission_classes = [permissions.AllowAny]

    def post(self, request: HttpRequest, **kwargs):
        # Verify incoming requests from Slack
        # https://api.slack.com/authentication/verifying-requests-from-slack
        if not signature_verifier.is_valid(
            body=request.body,
            timestamp=request.headers.get("X-Slack-Request-Timestamp"),
            signature=request.headers.get("X-Slack-Signature"),
        ):
            return Response("invalid request", status=status.HTTP_400_BAD_REQUEST)

        data = request.data

        data_type = data.get("type", "")
        # Check if it's a WhatsApp status update
        if (
            data.get("entry", [{}])[0]
            .get("changes", [{}])[0]
            .get("value", {})
            .get("statuses")
        ):
            print("Received a WhatsApp status update.")
            return Response(status=status.HTTP_200_OK)
        elif data_type == "url_verification":
            challenge = data.get("challenge")
            return Response({"challenge": challenge}, status=status.HTTP_200_OK)
        if is_valid_whatsapp_message(data):
            process_whatsapp_message(data)
            return Response(status=status.HTTP_200_OK)
        elif is_valid_slack_message(data):
            process_slack_message(data)
            return Response(status=status.HTTP_200_OK)
        return Response({"message": "No event"}, status=status.HTTP_200_OK)
