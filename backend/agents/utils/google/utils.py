import os
from typing import List, Optional

import google_auth_oauthlib
from django.conf import settings
from google.oauth2.credentials import Credentials

from langchain_community.tools.gmail.utils import (
    import_google,
    import_installed_app_flow,
)
from langchain_community.tools.gmail.utils import build_resource_service
# from langchain_community.agent_toolkits import GmailToolkit
from langchain_community.agent_toolkits.gmail.toolkit import GmailToolkit
# from langchain_google_genai import ChatGoogleGenerativeAI

from .tools import GoogleDriveTools, GoogleCalenderTools
from common.models import ThirdParty
from agents.utils.main import create_agent, create_prompt

GMAIL_SCOPES = ["https://mail.google.com/"]
GOOGLE_CALENDER_SCOPES = ["https://www.googleapis.com/auth/calender"]
# GeminiLLM = ChatGoogleGenerativeAI(
#     model="gemini-pro", google_api_key=settings.GOOGLE_API_KEY
# )


def get_credentials(
    token_file: Optional[str] = None,
    client_secrets_file: Optional[str] = None,
    scopes: Optional[List[str]] = None,
) -> Credentials:
    """Get credentials."""
    # From https://developers.google.com/gmail/api/quickstart/python
    Request, Credentials = import_google()
    InstalledAppFlow = import_installed_app_flow()
    creds = None
    scopes = scopes
    token_file = token_file or settings.DEFAULT_CREDS_TOKEN_FILE
    client_secrets_file = client_secrets_file or settings.DEFAULT_CLIENT_SECRETS_FILE
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, scopes)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # https://developers.google.com/gmail/api/quickstart/python#authorize_credentials_for_a_desktop_application # noqa
            flow = InstalledAppFlow.from_client_secrets_file(
                client_secrets_file, scopes
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(token_file, "w") as token:
            token.write(creds.to_json())
    return creds


credentials = get_credentials(
    token_file="token.json",
    scopes=["https://mail.google.com/"],
    client_secrets_file=settings.DEFAULT_CLIENT_SECRETS_FILE,
)
api_resource = build_resource_service(credentials=credentials, service_name="gmail", service_version="v1")
toolkit = GoogleDriveTools(creds=api_resource)


def google_oauth(thirdparty, gen_state, user_email):
    if thirdparty == ThirdParty.GMAIL:
        flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
            settings.DEFAULT_CLIENT_SECRETS_FILE,
            scopes = GMAIL_SCOPES
        )
    elif thirdparty == ThirdParty.GOOGLE_CALENDER:
        flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
            settings.DEFAULT_CLIENT_SECRETS_FILE,
            scopes = GOOGLE_CALENDER_SCOPES
        )
    flow.redirect_uri = settings.AGENT_REDIRECT_URI
    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        state=gen_state,
        login_hint=user_email,
        prompt="consent"
    )
    return auth_url, state


def google_oauth_callback(thirdparty, state):
    if thirdparty == ThirdParty.GMAIL:
        flow = google_auth_oauthlib.flow.Flow.from_client_config().from_client_secrets_file(
            settings.DEFAULT_CLIENT_SECRETS_FILE,
            scopes = GMAIL_SCOPES,
            state=state
        )
    elif thirdparty == ThirdParty.GOOGLE_CALENDER:
        flow = google_auth_oauthlib.flow.Flow.from_client_config().from_client_secrets_file(
            settings.DEFAULT_CLIENT_SECRETS_FILE,
            scopes = GOOGLE_CALENDER_SCOPES,
            state=state
        )
    flow.redirect_uri = settings.AGENT_REDIRECT_URI
    credentials = flow.credentials
    return credentials


def get_agent(thirdparty: ThirdParty):
    tools = []

    if thirdparty == ThirdParty.GMAIL:
        credential = None
        toolkit = GmailToolkit()
        toolkit.api_resource = credential
    elif thirdparty == ThirdParty.GOOGLE_CALENDER:
        credential = None
        toolkit = GoogleCalenderTools(credential)
    tools = toolkit.get_tools()
    prompt = create_prompt()
    agent = create_agent(prompt, GeminiLLM, tools)
    return agent
    