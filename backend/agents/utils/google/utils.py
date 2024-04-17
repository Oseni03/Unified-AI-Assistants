import os
from typing import List, Optional

from django.conf import settings

from google.oauth2.credentials import Credentials

from langchain_community.tools.gmail.utils import (
    import_google,
    import_installed_app_flow,
)


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
    scopes = scopes or settings.GOOGLE_SCOPES
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


def create_workspace_crew(access_token):
    pass