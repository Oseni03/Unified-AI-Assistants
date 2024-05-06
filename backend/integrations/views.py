from django.conf import settings
from django.shortcuts import get_object_or_404, redirect
from django.http import HttpRequest

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics, permissions

from slack_sdk.errors import SlackApiError
from slack_sdk.signature import SignatureVerifier
from slack_sdk import WebClient

from agents.utils.utils import credentials_to_dict, get_agent
from agents.serializers import AgentSerializer
from common.models import State

from .utils import save_bot
from .models import Bot, Integration, Agent
from .serializers import BotSerializer, EventSerializer


# Create your views here.
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
                bot = save_bot(agent, oauth_response, client)

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


class EventView(generics.GenericAPIView):
    """Token Lookup"""

    permission_classes = [permissions.AllowAny]
    serializer_class = EventSerializer

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

        if data.get("type") == "url_verification":
            challenge = data.get("challenge")
            return Response({"challenge": challenge}, status=status.HTTP_200_OK)

        if "event" in data:
            event = data.get("event")

            # in the case where this app gets a request from an Enterprise Grid workspace
            enterprise_id = data.get("enterprise_id")
            print(f"Enterprise ID: {enterprise_id}")
            # The workspace's ID
            team_id = data.get("team_id")
            user_id = event.get("user")
            query = event.get("text")
            channel = event.get("channel")
            thread_ts = event.get("ts")

            # Lookup the stored bot token for this workspace
            try:
                bot = Bot.objects.get(
                    user_id=user_id,
                    team_id=team_id,
                )
            except:
                return Response(status=status.HTTP_200_OK)

            agent = bot.agent
            bot_token = bot.access_token
            print(f"Bot Token: {bot_token}")
            if not bot_token:
                # The app may be uninstalled or be used in a shared channel
                return Response(
                    "Please install this app first!", status=status.HTTP_200_OK
                )

            client = WebClient(token=bot_token)
            bot_id = client.api_call("auth.test")["user_id"]

            # Ignore bot's own message
            if user_id == bot_id:
                return Response(status=status.HTTP_200_OK)

            # Post an initial message
            result = client.chat_postMessage(
                channel=channel, text=":mag: Searching...", thread_ts=thread_ts
            )
            thread_ts = result.get("ts")

            # Fetch response using RemoteRunnable
            agent_executor = get_agent(agent.integration, agent.credentials)
            response = agent_executor.invoke({"input": query})

            # Process response and send follow-up message
            output_text = response[
                "output"
            ]  # Adjust according to your actual response structure

            # Update the initial message with the response and use mrkdown block section to return the response in Slack markdown format
            # client.chat_update(
            client.chat_postMessage(
                channel=channel,
                ts=thread_ts,
                text=output_text,
                blocks=[
                    {"type": "section", "text": {"type": "mrkdwn", "text": output_text}}
                ],
            )
            serializer = self.get_serializer({"query": query, "response": output_text})

            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response({"message": "No event"}, status=status.HTTP_200_OK)
