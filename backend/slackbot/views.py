import html
import json
import uuid

from django.conf import settings

from rest_framework import status, generics, permissions
from rest_framework.response import Response

from slack_sdk.errors import SlackApiError
from slack_sdk.signature import SignatureVerifier
from slack_sdk import WebClient
from slack_sdk.oauth import AuthorizeUrlGenerator

from .models import Installation, State


# Build https://slack.com/oauth/v2/authorize with sufficient query parameters
authorize_url_generator = AuthorizeUrlGenerator(
    client_id=settings.SLACK_CLIENT_ID,
    scopes=settings.SLACK_SCOPES,
    user_scopes=["search:read"],
)


# Create your views here.
class OAUTHView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, **kwargs):
        # Generate a random value and store it on the server-side
        state = str(State.issue())
        # https://slack.com/oauth/v2/authorize?state=(generated value)&client_id={client_id}&scope=app_mentions:read,chat:write&user_scope=search:read
        url = authorize_url_generator.generate(state)
        button = f'''<a href="{html.escape(url)}">
            <img 
                alt="Add to Slack" 
                height="40" 
                width="139" 
                src="https://platform.slack-edge.com/img/add_to_slack.png" 
                srcset="https://platform.slack-edge.com/img/add_to_slack.png 1x, https://platform.slack-edge.com/img/add_to_slack@2x.png 2x" />
        </a>'''
        return {"button": button}


class OAUTHCallbackView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]

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
                installed_enterprise = oauth_response.get("enterprise") or {}
                is_enterprise_install = oauth_response.get("is_enterprise_install")
                installed_team = oauth_response.get("team") or {}
                installer = oauth_response.get("authed_user") or {}
                incoming_webhook = oauth_response.get("incoming_webhook") or {}
                bot_token = oauth_response.get("access_token")
                # NOTE: oauth.v2.access doesn't include bot_id in response
                bot_id = None
                enterprise_url = None
                if bot_token is not None:
                    auth_test = client.auth_test(token=bot_token)
                    bot_id = auth_test["bot_id"]
                    if is_enterprise_install is True:
                        enterprise_url = auth_test.get("url")

                installation = Installation(
                    app_id=oauth_response.get("app_id"),
                    enterprise_id=installed_enterprise.get("id"),
                    enterprise_name=installed_enterprise.get("name"),
                    enterprise_url=enterprise_url,
                    team_id=installed_team.get("id"),
                    team_name=installed_team.get("name"),
                    bot_token=bot_token,
                    bot_id=bot_id,
                    bot_user_id=oauth_response.get("bot_user_id"),
                    bot_scopes=oauth_response.get("scope"),  # comma-separated string
                    user_id=installer.get("id"),
                    user_token=installer.get("access_token"),
                    user_scopes=installer.get("scope"),  # comma-separated string
                    incoming_webhook_url=incoming_webhook.get("url"),
                    incoming_webhook_channel=incoming_webhook.get("channel"),
                    incoming_webhook_channel_id=incoming_webhook.get("channel_id"),
                    incoming_webhook_configuration_url=incoming_webhook.get("configuration_url"),
                    is_enterprise_install=is_enterprise_install,
                    token_type=oauth_response.get("token_type"),
                )

                # Store the installation
                installation.save()

                return Response({"message": "Thanks for installing this app!"}, status=status.HTTP_200_OK)
            else:
                return Response({"message": "Try the installation again (the state value is already expired)"}, status=status.HTTP_400_BAD_REQUEST)

        error = request.args["error"] if "error" in request.args else ""
        return Response(f"Something is wrong with the installation (error: {html.escape(error)})", status=status.HTTP_400_BAD_REQUEST)
    


signature_verifier = SignatureVerifier(signing_secret=settings.SLACK_SIGNING_SECRET)


class EventView(generics.GenericAPIView):
    """ Token Lookup"""

    permission_classes = [permissions.AllowAny]

    def post(self, request, **kwargs):
        # Verify incoming requests from Slack
        # https://api.slack.com/authentication/verifying-requests-from-slack
        if not signature_verifier.is_valid(
            body=request.get_data(),
            timestamp=request.headers.get("X-Slack-Request-Timestamp"),
            signature=request.headers.get("X-Slack-Signature")):
            return Response("invalid request", status=status.HTTP_400_BAD_REQUEST)

        # Handle a slash command invocation
        if "command" in request.form \
            and request.form["command"] == "/open-modal":
            try:
                # in the case where this app gets a request from an Enterprise Grid workspace
                enterprise_id = request.form.get("enterprise_id")
                # The workspace's ID
                team_id = request.form["team_id"]
                # Lookup the stored bot token for this workspace
                bot = Installation.objects.get(
                    enterprise_id=enterprise_id,
                    team_id=team_id,
                )
                bot_token = bot.bot_token if bot else None
                if not bot_token:
                    # The app may be uninstalled or be used in a shared channel
                    return Response("Please install this app first!", status=status.HTTP_200_OK)

                # Open a modal using the valid bot token
                client = WebClient(token=bot_token)
                trigger_id = request.form["trigger_id"]
                response = client.views_open(
                    trigger_id=trigger_id,
                    view={
                        "type": "modal",
                        "callback_id": "modal-id",
                        "title": {
                            "type": "plain_text",
                            "text": "Awesome Modal"
                        },
                        "submit": {
                            "type": "plain_text",
                            "text": "Submit"
                        },
                        "blocks": [
                            {
                                "type": "input",
                                "block_id": "b-id",
                                "label": {
                                    "type": "plain_text",
                                    "text": "Input label",
                                },
                                "element": {
                                    "action_id": "a-id",
                                    "type": "plain_text_input",
                                }
                            }
                        ]
                    }
                )
                return Response("", status.HTTP_200_OK)
            except SlackApiError as e:
                code = e.response["error"]
                return Response(f"Failed to open a modal due to {code}", status=status.HTTP_200_OK)

        elif "payload" in request.form:
            # Data submission from the modal
            payload = json.loads(request.form["payload"])
            if payload["type"] == "view_submission" \
                and payload["view"]["callback_id"] == "modal-id":
                submitted_data = payload["view"]["state"]["values"]
                print(submitted_data)  # {'b-id': {'a-id': {'type': 'plain_text_input', 'value': 'your input'}}}
                # You can use WebClient with a valid token here too
                return Response("", status=status.HTTP_200_OK)

        # Indicate unsupported request patterns
        return Response("", status=status.HTTP_404_NOT_FOUND)