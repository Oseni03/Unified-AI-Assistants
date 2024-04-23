import html
import json
import uuid

from django.conf import settings

from django.shortcuts import get_object_or_404
from rest_framework import status, generics, permissions
from rest_framework.response import Response

from slack_sdk.errors import SlackApiError
from slack_sdk.signature import SignatureVerifier
from slack_sdk import WebClient
from slack_sdk.oauth import AuthorizeUrlGenerator

from agents.models import Agent
from common.models import State, ThirdParty

from .utils import fetch_response, save_bot
from .models import Bot
from .serializers import BotSerializer, EventSerializer, OAuthURLSerializer


# Build https://slack.com/oauth/v2/authorize with sufficient query parameters
authorize_url_generator = AuthorizeUrlGenerator(
    client_id=settings.SLACK_CLIENT_ID,
    scopes=settings.SLACK_SCOPES,
    user_scopes=["search:read"],
)


# Create your views here.
class OAUTHView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = OAuthURLSerializer

    def get(self, request, thirdparty, agent_id, **kwargs):
        request.session["agent_id"] = agent_id
        # Generate a random value and store it on the server-side
        state = str(State.issue(thirdparty))
        if thirdparty == ThirdParty.SLACK:
            # https://slack.com/oauth/v2/authorize?state=(generated value)&client_id={client_id}&scope=app_mentions:read,chat:write&user_scope=search:read
            url = authorize_url_generator.generate(state)
            serializer = self.serializer_class(data={"url": url})
            button = f'''<a href="{html.escape(url)}">
                <img 
                    alt="Add to Slack" 
                    height="40" 
                    width="139" 
                    src="https://platform.slack-edge.com/img/add_to_slack.png" 
                    srcset="https://platform.slack-edge.com/img/add_to_slack.png 1x, https://platform.slack-edge.com/img/add_to_slack@2x.png 2x" />
            </a>'''
        return Response(serializer.data, status=status.HTTP_200_OK)


class OAUTHCallbackView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = BotSerializer

    def get(self, request, **kwargs):
        # Retrieve the auth code and state from the request params
        if "code" in request.args:
            # Verify the state parameter
            if State.consume(uuid.UUID(request.args["state"]).hex):
                client = WebClient()  # no prepared token needed for this
                # Complete the installation by calling oauth.v2.access API method
                oauth_response = client.oauth_v2_access(
                    client_id=settings.SLACK_CLIENT_ID,
                    client_secret=settings.SLACK_CLIENT_SECRET,
                    # redirect_uri=redirect_uri,
                    code=request.args["code"]
                )

                agent_id = request.session.get("agent_id")
                agent = get_object_or_404(Agent, id=agent_id)
                
                bot = save_bot(agent, oauth_response, client)

                serializer = self.get_serializer(instance=bot)

                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response({"message": "Try the installation again (the state value is already expired)"}, status=status.HTTP_400_BAD_REQUEST)

        error = request.args["error"] if "error" in request.args else ""
        return Response(f"Something is wrong with the installation (error: {html.escape(error)})", status=status.HTTP_400_BAD_REQUEST)
    


signature_verifier = SignatureVerifier(signing_secret=settings.SLACK_SIGNING_SECRET)


class EventView(generics.GenericAPIView):
    """ Token Lookup"""

    permission_classes = [permissions.AllowAny]
    serializer_class = EventSerializer

    def post(self, request, **kwargs):
        print(request.data) 

        # Verify incoming requests from Slack
        # https://api.slack.com/authentication/verifying-requests-from-slack
        if not signature_verifier.is_valid(
            body=request.get_data(),
            timestamp=request.headers.get("X-Slack-Request-Timestamp"),
            signature=request.headers.get("X-Slack-Signature")):
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

        channel_id = request.form['channel']
        thread_ts = request.form['ts']
        user_id = request.form["user"]
        query = request.form.get("text")

        if user_id == bot_id: # OR if request.form.get('subtype') == 'bot_message':
            return Response({}, status=status.HTTP_200_OK)

        # Post an initial message
        result = client.chat_postpayload(channel=channel_id, text=":mag: Searching...", thread_ts=thread_ts)
        thread_ts = result["ts"]
        
        # Fetch response using RemoteRunnable
        response = fetch_response(query)

        # Process response and send follow-up message
        output_text = response['output']  # Adjust according to your actual response structure

        #Update the initial message with the response and use mrkdown block section to return the response in Slack markdown format
        client.chat_update(
            channel=channel_id,
            ts=thread_ts,
            text=output_text,
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": output_text
                    }
                }
            ]
        )

        resp_data = {
            "query": query,
            "response": {
                "mrkdwn": output_text,
            }
        }
        serializer = self.get_serializer({"query": query, "response": output_text})

        return Response(serializer.data, status=status.HTTP_200_OK)