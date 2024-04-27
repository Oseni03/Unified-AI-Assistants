import html
import uuid

from django.conf import settings
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics, permissions

from slack_sdk.errors import SlackApiError
from slack_sdk.signature import SignatureVerifier
from slack_sdk import WebClient

from agents.models import Agent
from common.models import State, ThirdParty

from .utils import fetch_response, save_bot, create_slack_installation_url
from .models import Bot, Integration
from .serializers import BotSerializer, EventSerializer


# Create your views here.
class OAUTHView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, thirdparty, agent_id, **kwargs):
        request.session["agent_id"] = agent_id
        # Generate a random value and store it on the server-side
        state = State().issue(thirdparty)
        request.session["thirdparty"] = thirdparty  # Add to the session
        request.session["state"] = state  # Add to the session

        integration = Integration.objects.get(thirdparty=thirdparty)
        auth_url = integration.get_oauth_url(state=state, user_email=request.user.email)
        print(auth_url)
        return redirect(auth_url)


class OAUTHCallbackView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = BotSerializer

    def get(self, request, **kwargs):
        try:
            # Ensure that the request is not a forgery and that the user sending
            # this connect request is the expected user.
            state = request.GET.get("state", "")
            code = request.GET.get("code", "")

            gen_state = request.session.get("state")
            thirdparty = request.session.get("thirdparty")
            agent_id = request.session.get("agent_id")

            print(
                f"State: {state}\nCode: {code}\nThirdparty: {thirdparty}\nAgent-ID: {agent_id}"
            )

            if not (state == gen_state):
                return Response(
                    "Invalid state parameter.", status=status.HTTP_401_UNAUTHORIZED
                )

            State.consume(state)

            integration = Integration.objects.get(thirdparty=thirdparty)
            client = WebClient()
            oauth_response = integration.handle_oauth_callback(
                state, code, client=client
            )

            agent = get_object_or_404(Agent, id=agent_id)
            bot = save_bot(agent, oauth_response, client)

            serializer = self.get_serializer(instance=bot)

            return Response(serializer.data, status=status.HTTP_200_OK)
        except:
            error = request.GET.get("error", "")
            return Response(
                f"Something is wrong with the installation (error: {html.escape(error)})",
                status=status.HTTP_400_BAD_REQUEST,
            )


signature_verifier = SignatureVerifier(signing_secret=settings.SLACK_SIGNING_SECRET)


class EventView(generics.GenericAPIView):
    """Token Lookup"""

    permission_classes = [permissions.AllowAny]
    serializer_class = EventSerializer

    def post(self, request, **kwargs):
        print(request.data)

        # Verify incoming requests from Slack
        # https://api.slack.com/authentication/verifying-requests-from-slack
        if not signature_verifier.is_valid(
            body=request.get_data(),
            timestamp=request.headers.get("X-Slack-Request-Timestamp"),
            signature=request.headers.get("X-Slack-Signature"),
        ):
            return Response("invalid request", status=status.HTTP_400_BAD_REQUEST)

        print(request.form)
        print(request.data)

        # in the case where this app gets a request from an Enterprise Grid workspace
        enterprise_id = request.form.get("enterprise_id")
        # The workspace's ID
        team_id = request.form["team_id"]

        # Lookup the stored bot token for this workspace
        bot = Bot.objects.filter(
            enterprise_id=enterprise_id,
            team_id=team_id,
        )
        bot_token = bot.first().bot_token if bot.exists() else None
        if not bot_token:
            # The app may be uninstalled or be used in a shared channel
            return Response("Please install this app first!", status=status.HTTP_200_OK)

        client = WebClient(token=bot_token)
        bot_id = client.api_call("auth.test")["user_id"]
        trigger_id = request.form["trigger_id"]

        channel_id = request.form["channel"]
        thread_ts = request.form["ts"]
        user_id = request.form["user"]
        query = request.form.get("text")

        if user_id == bot_id:  # OR if request.form.get('subtype') == 'bot_message':
            return Response({}, status=status.HTTP_200_OK)

        # Post an initial message
        result = client.chat_postpayload(
            channel=channel_id, text=":mag: Searching...", thread_ts=thread_ts
        )
        thread_ts = result["ts"]

        # Fetch response using RemoteRunnable
        response = fetch_response(query)

        # Process response and send follow-up message
        output_text = response[
            "output"
        ]  # Adjust according to your actual response structure

        # Update the initial message with the response and use mrkdown block section to return the response in Slack markdown format
        client.chat_update(
            channel=channel_id,
            ts=thread_ts,
            text=output_text,
            blocks=[
                {"type": "section", "text": {"type": "mrkdwn", "text": output_text}}
            ],
        )

        resp_data = {
            "query": query,
            "response": {
                "mrkdwn": output_text,
            },
        }
        serializer = self.get_serializer({"query": query, "response": output_text})

        return Response(serializer.data, status=status.HTTP_200_OK)
