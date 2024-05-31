import base64
import datetime
import email
from enum import Enum
import io
import uuid
from httplib2 import Http
from typing import Any, Dict, List, Optional, Type, Union
from django.conf import settings
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from simple_salesforce import Salesforce

from langchain.tools import tool
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_community.tools.gmail.utils import clean_email_body
from langchain_core.callbacks import CallbackManagerForToolRun

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload


class Resource(str, Enum):
    """Enumerator of Resources to search."""

    THREADS = "threads"
    MESSAGES = "messages"


class CreateDraftSchema(BaseModel):
    """Input for CreateDraftTool."""

    message: str = Field(
        ...,
        description="The message to include in the draft.",
    )
    to: List[str] = Field(
        ...,
        description="The list of recipients.",
    )
    subject: str = Field(
        ...,
        description="The subject of the message.",
    )
    cc: Optional[List[str]] = Field(
        None,
        description="The list of CC recipients.",
    )
    bcc: Optional[List[str]] = Field(
        None,
        description="The list of BCC recipients.",
    )


class SendMessageSchema(BaseModel):
    """Input for SendMessageTool."""

    message: str = Field(
        ...,
        description="The message to send.",
    )
    to: Union[str, List[str]] = Field(
        ...,
        description="The list of recipients.",
    )
    subject: str = Field(
        ...,
        description="The subject of the message.",
    )
    cc: Optional[Union[str, List[str]]] = Field(
        None,
        description="The list of CC recipients.",
    )
    bcc: Optional[Union[str, List[str]]] = Field(
        None,
        description="The list of BCC recipients.",
    )


class GetMessageSchema(BaseModel):
    """Input for GetMessageTool."""

    message_id: str = Field(
        ...,
        description="The unique ID of the email message, retrieved from a search.",
    )


class SearchArgsSchema(BaseModel):
    """Input for SearchGmailTool."""

    # From https://support.google.com/mail/answer/7190?hl=en
    query: str = Field(
        ...,
        description="The Gmail query. Example filters include from:sender,"
        " to:recipient, subject:subject, -filtered_term,"
        " in:folder, is:important|read|starred, after:year/mo/date, "
        "before:year/mo/date, label:label_name"
        ' "exact phrase".'
        " Search newer/older than using d (day), m (month), and y (year): "
        "newer_than:2d, older_than:1y."
        " Attachments with extension example: filename:pdf. Multiple term"
        " matching example: from:amy OR from:david.",
    )
    resource: Resource = Field(
        default=Resource.MESSAGES,
        description="Whether to search for threads or messages.",
    )
    max_results: int = Field(
        default=10,
        description="The maximum number of results to return.",
    )


class GetThreadSchema(BaseModel):
    """Input for GetMessageTool."""

    # From https://support.google.com/mail/answer/7190?hl=en
    thread_id: str = Field(
        ...,
        description="The thread ID.",
    )


class GmailTools:
    def __init__(self, creds: Credentials) -> None:
        self.service = build("gmail", "v1", credentials=creds)
    
    def _prepare_draft_message(
        self,
        message: str,
        to: List[str],
        subject: str,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
    ) -> dict:
        draft_message = EmailMessage()
        draft_message.set_content(message)

        draft_message["To"] = ", ".join(to)
        draft_message["Subject"] = subject
        if cc is not None:
            draft_message["Cc"] = ", ".join(cc)

        if bcc is not None:
            draft_message["Bcc"] = ", ".join(bcc)

        encoded_message = base64.urlsafe_b64encode(draft_message.as_bytes()).decode()
        return {"message": {"raw": encoded_message}}
    
    @tool(args_schema=CreateDraftSchema)
    def create_draft(
        self,
        message: str,
        to: List[str],
        subject: str,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
    ) -> dict:
        """Tool that creates a draft email for Gmail.
        
        Use this tool to create a draft email with the provided message fields."""
        
        try:
            create_message = self._prepare_draft_message(message, to, subject, cc, bcc)
            draft = (
                self.service.users()
                .drafts()
                .create(userId="me", body=create_message)
                .execute()
            )
            output = f'Draft created. Draft Id: {draft["id"]}'
            return output
        except Exception as e:
            raise Exception(f"An error occurred: {e}")
    
    def _prepare_message(
        self,
        message: str,
        to: Union[str, List[str]],
        subject: str,
        cc: Optional[Union[str, List[str]]] = None,
        bcc: Optional[Union[str, List[str]]] = None,
    ) -> Dict[str, Any]:
        """Create a message for an email."""
        mime_message = MIMEMultipart()
        mime_message.attach(MIMEText(message, "html"))

        mime_message["To"] = ", ".join(to if isinstance(to, list) else [to])
        mime_message["Subject"] = subject
        if cc is not None:
            mime_message["Cc"] = ", ".join(cc if isinstance(cc, list) else [cc])

        if bcc is not None:
            mime_message["Bcc"] = ", ".join(bcc if isinstance(bcc, list) else [bcc])

        encoded_message = base64.urlsafe_b64encode(mime_message.as_bytes()).decode()
        return {"raw": encoded_message}

    @tool(args_schema=SendMessageSchema)
    def send_message(
        self,
        message: str,
        to: Union[str, List[str]],
        subject: str,
        cc: Optional[Union[str, List[str]]] = None,
        bcc: Optional[Union[str, List[str]]] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Tool that sends a message to Gmail.
        
        Use this tool to send email messages. The input is the message, recipients"""
        try:
            create_message = self._prepare_message(message, to, subject, cc=cc, bcc=bcc)
            send_message = (
                self.service.users()
                .messages()
                .send(userId="me", body=create_message)
            )
            sent_message = send_message.execute()
            return f'Message sent. Message Id: {sent_message["id"]}'
        except Exception as error:
            raise Exception(f"An error occurred: {error}")
    
    def _parse_threads(self, threads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # Add the thread message snippets to the thread results
        results = []
        for thread in threads:
            thread_id = thread["id"]
            thread_data = (
                self.api_resource.users()
                .threads()
                .get(userId="me", id=thread_id)
                .execute()
            )
            messages = thread_data["messages"]
            thread["messages"] = []
            for message in messages:
                snippet = message["snippet"]
                thread["messages"].append({"snippet": snippet, "id": message["id"]})
            results.append(thread)

        return results

    def _parse_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        results = []
        for message in messages:
            message_id = message["id"]
            message_data = (
                self.api_resource.users()
                .messages()
                .get(userId="me", format="raw", id=message_id)
                .execute()
            )

            raw_message = base64.urlsafe_b64decode(message_data["raw"])

            email_msg = email.message_from_bytes(raw_message)

            subject = email_msg["Subject"]
            sender = email_msg["From"]

            message_body = ""
            if email_msg.is_multipart():
                for part in email_msg.walk():
                    ctype = part.get_content_type()
                    cdispo = str(part.get("Content-Disposition"))
                    if ctype == "text/plain" and "attachment" not in cdispo:
                        try:
                            message_body = part.get_payload(decode=True).decode("utf-8")
                        except UnicodeDecodeError:
                            message_body = part.get_payload(decode=True).decode(
                                "latin-1"
                            )
                        break
            else:
                message_body = email_msg.get_payload(decode=True).decode("utf-8")

            body = clean_email_body(message_body)

            results.append(
                {
                    "id": message["id"],
                    "threadId": message_data["threadId"],
                    "snippet": message_data["snippet"],
                    "body": body,
                    "subject": subject,
                    "sender": sender,
                }
            )
        return results

    @tool(args_schema=SearchArgsSchema)
    def search(
        self,
        query: str,
        resource: Resource = Resource.MESSAGES,
        max_results: int = 10,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> List[Dict[str, Any]]:
        """Tool that searches for messages or threads in Gmail.
        
        The Gmail query. Example filters include from:sender,
        to:recipient, subject:subject, -filtered_term,
        in:folder, is:important|read|starred, after:year/mo/date, 
        before:year/mo/date, label:label_name
        "exact phrase".
        Search newer/older than using d (day), m (month), and y (year): 
        newer_than:2d, older_than:1y.
        Attachments with extension example: filename:pdf. Multiple term
        matching example: from:amy OR from:david."""

        results = (
            self.service.users()
            .messages()
            .list(userId="me", q=query, maxResults=max_results)
            .execute()
            .get(resource.value, [])
        )
        if resource == Resource.THREADS:
            return self._parse_threads(results)
        elif resource == Resource.MESSAGES:
            return self._parse_messages(results)
        else:
            raise NotImplementedError(f"Resource of type {resource} not implemented.")
    
    @tool(args_schema=GetMessageSchema)
    def get_message(
        self,
        message_id: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> Dict:
        """Tool that gets a message by ID from Gmail.

        Use this tool to fetch an email by message ID.
        Returns the thread ID, snippet, body, subject, and sender."""

        query = (
            self.service.users()
            .messages()
            .get(userId="me", format="raw", id=message_id)
        )
        message_data = query.execute()
        raw_message = base64.urlsafe_b64decode(message_data["raw"])

        email_msg = email.message_from_bytes(raw_message)

        subject = email_msg["Subject"]
        sender = email_msg["From"]

        message_body = ""
        if email_msg.is_multipart():
            for part in email_msg.walk():
                ctype = part.get_content_type()
                cdispo = str(part.get("Content-Disposition"))
                if ctype == "text/plain" and "attachment" not in cdispo:
                    message_body = part.get_payload(decode=True).decode("utf-8")
                    break
        else:
            message_body = email_msg.get_payload(decode=True).decode("utf-8")

        body = clean_email_body(message_body)

        return {
            "id": message_id,
            "threadId": message_data["threadId"],
            "snippet": message_data["snippet"],
            "body": body,
            "subject": subject,
            "sender": sender,
        }
    
    @tool(args_schema=GetThreadSchema)
    def get_thread(
        self,
        thread_id: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> Dict:
        """Tool that gets a thread by ID from Gmail.
        
        Use this tool to search for email messages."
        The input must be a valid Gmail query.
        The output is a JSON list of messages."""

        query = self.service.users().threads().get(userId="me", id=thread_id)
        thread_data = query.execute()
        if not isinstance(thread_data, dict):
            raise ValueError("The output of the query must be a list.")
        messages = thread_data["messages"]
        thread_data["messages"] = []
        keys_to_keep = ["id", "snippet", "snippet"]
        # TODO: Parse body.
        for message in messages:
            thread_data["messages"].append(
                {k: message[k] for k in keys_to_keep if k in message}
            )
        return thread_data


class GoogleCalenderTools:
    def __init__(self, creds: Credentials) -> None:
        self.service = build("calender", "v3", credentials=creds)

    @tool
    def get_event_list(
        self,
        calender_id: str = "primary",
        time: datetime.datetime = datetime.datetime.now(datetime.UTC).isoformat() + "Z",
        max_result: int = 10,
    ):
        """Get list of calender events in google calender"""
        print("Getting the upcoming 10 events")
        events_result = (
            self.service.events()
            .list(
                calendarId=calender_id,
                timeMin=time,
                maxResults=max_result,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        events = events_result.get("items", [])
        return events
    
    def get_tools(self) -> List:
        """Get the tools in the toolkit."""
        return [
            self.get_event_list,
        ]


class GoogleDocTools:
    def __init__(self, creds: Credentials) -> None:
        self.service = build("docs", "v1", credentials=creds)

    @tool
    def retrieve_document(self, document_id: int):
        """Retrieve a document in google doc"""
        # Retrieve the documents contents from the Docs service.
        document = self.service.documents().get(documentId=document_id).execute()
        # to_json = json.dumps(document, indent=4, sort_keys=True)
        return document
    
    def get_tools(self) -> List:
        """Get the tools in the toolkit."""
        return [
            self.retrieve_document,
        ]


class GoogleDriveTools:
    def __init__(self, creds: Credentials) -> None:
        self.service = build("drive", "v3", credentials=creds)

    @tool
    def get_file_list(self, page_size=10):
        """get list of files in google drive"""
        # Call the Drive v3 API
        results = (
            self.service.files()
            .list(page_size=10, fields="nextPageToken, files(id, name)")
            .execute()
        )
        items = results.get("files", [])
        return items

    @tool
    def create_drive(self, name: str):
        """Create a drive.
        Returns:
            Id of the created drive"""

        drive_metadata = {"name": name}
        request_id = str(uuid.uuid4())
        # pylint: disable=maybe-no-member
        drive = (
            self.service.drives()
            .create(body=drive_metadata, requestId=request_id, fields="id")
            .execute()
        )
        print(f'Drive ID: {drive.get("id")}')
        drive["name"] = name
        return drive

    @tool("Find all shared drives without an organizer and add one")
    def recover_drives(self, user_email_address: str):
        """Find all shared drives without an organizer and add one.
        Args:
            real_user:User ID for the new organizer.
        Returns:
            drives object"""

        try:
            drives = []

            # pylint: disable=maybe-no-member
            page_token = None
            new_organizer_permission = {
                "type": "user",
                "role": "organizer",
                "emailAddress": "user@example.com",
            }
            new_organizer_permission["emailAddress"] = user_email_address

            while True:
                response = (
                    self.service.drives()
                    .list(
                        q="organizerCount = 0",
                        fields="nextPageToken, drives(id, name)",
                        useDomainAdminAccess=True,
                        pageToken=page_token,
                    )
                    .execute()
                )
                for drive in response.get("drives", []):
                    print(
                        "Found shared drive without organizer: "
                        f"{drive.get('title')}, {drive.get('id')}"
                    )
                    permission = (
                        self.service.permissions()
                        .create(
                            fileId=drive.get("id"),
                            body=new_organizer_permission,
                            useDomainAdminAccess=True,
                            supportsAllDrives=True,
                            fields="id",
                        )
                        .execute()
                    )
                    print(f'Added organizer permission: {permission.get("id")}')

                drives.extend(response.get("drives", []))
                page_token = response.get("nextPageToken", None)
                if page_token is None:
                    break

        except HttpError as error:
            print(f"An error occurred: {error}")
            drives = []

        return drives

    @tool
    def fetch_changes(self):
        """Retrieve the list of changes for the currently authenticated user.
            prints changed file's ID

        Returns: changes (changed files)
        """

        try:
            # Begin with our last saved start token for this user or the
            # current token from getStartPageToken()
            page_token = (
                self.service.changes()
                .getStartPageToken()
                .execute()
                .get("startPageToken")
            )
            # pylint: disable=maybe-no-member

            changes = []

            while page_token is not None:
                response = (
                    self.service.changes()
                    .list(pageToken=page_token, spaces="drive")
                    .execute()
                )
                for change in response.get("changes"):
                    # Process change
                    print(f'Change found for file: {change.get("fileId")}')
                    changes.append(change)
                if "newStartPageToken" in response:
                    # Last page, save this token for the next polling interval
                    saved_start_page_token = response.get("newStartPageToken")
                page_token = response.get("nextPageToken")

        except HttpError as error:
            print(f"An error occurred: {error}")
            changes = []

        return changes

    @tool
    def fetch_appdata_folder(self):
        """List out application data folder and prints folder ID.
        Returns : Folder ID
        """

        try:
            # pylint: disable=maybe-no-member
            file = (
                self.service.files().get(fileId="appDataFolder", fields="id").execute()
            )
            print(f'Folder ID: {file.get("id")}')

        except HttpError as error:
            print(f"An error occurred: {error}")
            file = None

        return file.id

    @tool
    def list_appdata(self):
        """List all files inserted in the application data folder
        prints file titles with Ids.
        Returns : List of items
        """

        try:
            # pylint: disable=maybe-no-member
            response = (
                self.service.files()
                .list(
                    spaces="appDataFolder",
                    fields="nextPageToken, files(id, name)",
                    pageSize=10,
                )
                .execute()
            )
            for file in response.get("files", []):
                # Process change
                print(f'Found file: {file.get("name")}, {file.get("id")}')

        except HttpError as error:
            print(f"An error occurred: {error}")
            response = None

        return response.get("files")

    @tool
    def upload_to_folder(self, file_name: str, mimetype: str, folder_id=None):
        """Insert a file in the application data folder and prints file Id.
        Args:
            file_name: file name
            mimetype: file mimetype
            folder_id: Id of the folder

        Returns : ID's of the inserted files
        """

        try:
            # pylint: disable=maybe-no-member
            if folder_id:
                parent_folder = [folder_id]
            else:
                parent_folder = ["appDataFolder"]

            file_metadata = {"name": file_name, "parents": parent_folder}
            media = MediaFileUpload(file_name, mimetype=mimetype, resumable=True)
            file = (
                self.service.files()
                .create(body=file_metadata, media_body=media, fields="id")
                .execute()
            )
            print(f'File ID: {file.get("id")}')
            return file.get("id")

        except HttpError as error:
            print(f"An error occurred: {error}")
            return None

    @tool
    def share_file(self, real_file_id, real_user, real_domain):
        """Batch permission modification.
        Args:
            real_file_id: file Id
            real_user: User ID
            real_domain: Domain of the user ID
        Prints modified permissions
        """

        try:
            # create drive api client
            ids = []
            file_id = real_file_id

            def callback(request_id, response, exception):
                if exception:
                    # Handle error
                    print(exception)
                else:
                    print(f"Request_Id: {request_id}")
                    print(f'Permission Id: {response.get("id")}')
                    ids.append(response.get("id"))

            batch = self.service.new_batch_http_request(callback=callback)
            user_permission = {
                "type": "user",
                "role": "writer",
                "emailAddress": "user@example.com",
            }
            user_permission["emailAddress"] = real_user
            batch.add(
                self.service.permissions().create(
                    fileId=file_id,
                    body=user_permission,
                    fields="id",
                )
            )
            domain_permission = {
                "type": "domain",
                "role": "reader",
                "domain": "example.com",
            }
            domain_permission["domain"] = real_domain
            batch.add(
                self.service.permissions().create(
                    fileId=file_id,
                    body=domain_permission,
                    fields="id",
                )
            )
            batch.execute()

        except HttpError as error:
            print(f"An error occurred: {error}")
            ids = None

        return ids

    @tool
    def search_file(self, mimetype="image/jpeg"):
        """Search file in drive location
        Args:
            mimetype: file mimetype
        """

        try:
            files = []
            page_token = None
            while True:
                # pylint: disable=maybe-no-member
                response = (
                    self.service.files()
                    .list(
                        q=f"mimeType='{mimetype}'",
                        spaces="drive",
                        fields="nextPageToken, files(id, name)",
                        pageToken=page_token,
                    )
                    .execute()
                )
                for file in response.get("files", []):
                    # Process change
                    print(f'Found file: {file.get("name")}, {file.get("id")}')
                files.extend(response.get("files", []))
                page_token = response.get("nextPageToken", None)
                if page_token is None:
                    break

        except HttpError as error:
            print(f"An error occurred: {error}")
            files = None

        return files

    @tool
    def move_file_to_folder(self, file_id, folder_id):
        """Move specified file to the specified folder.
        Args:
            file_id: Id of the file to move.
            folder_id: Id of the folder
        Print: An object containing the new parent folder and other meta data
        Returns : Parent Ids for the file
        """

        try:
            # pylint: disable=maybe-no-member
            # Retrieve the existing parents to remove
            file = self.service.files().get(fileId=file_id, fields="parents").execute()
            previous_parents = ",".join(file.get("parents"))
            # Move the file to the new folder
            file = (
                self.service.files()
                .update(
                    fileId=file_id,
                    addParents=folder_id,
                    removeParents=previous_parents,
                    fields="id, parents",
                )
                .execute()
            )
            return file.get("parents")

        except HttpError as error:
            print(f"An error occurred: {error}")
            return None

    @tool
    def export_pdf(self, real_file_id):
        """Download a Document file in PDF format.
        Args:
            real_file_id : file ID of any workspace document format file
        Returns : IO object with location
        """

        try:
            file_id = real_file_id

            # pylint: disable=maybe-no-member
            request = self.service.files().export_media(
                fileId=file_id, mimeType="application/pdf"
            )
            file = io.BytesIO()
            downloader = MediaIoBaseDownload(file, request)

            done = False
            while done is False:
                status, done = downloader.next_chunk()
                print(f"Download {int(status.progress() * 100)}.")

        except HttpError as error:
            print(f"An error occurred: {error}")
            file = None

        return file.getvalue()

    @tool
    def download_file(self, real_file_id):
        """Downloads a file
        Args:
            real_file_id: ID of the file to download
        Returns : IO object with location.
        """

        try:
            file_id = real_file_id

            # pylint: disable=maybe-no-member
            request = self.service.files().get_media(fileId=file_id)
            file = io.BytesIO()
            downloader = MediaIoBaseDownload(file, request)

            done = False
            while done is False:
                status, done = downloader.next_chunk()
                print(f"Download {int(status.progress() * 100)}.")
            return file.getvalue()

        except HttpError as error:
            print(f"An error occurred: {error}")
            return None

    @tool
    def duplicate_file(self, origin_file_id, title):
        """Duplicate a file
        Args:
            origin_file_id: ID of the file to duplicate
            title: Title of the new copied file
        """

        try:
            copied_file = {"title": "my_copy"}
            results = (
                self.service.files()
                .copy(fileId=origin_file_id, body=copied_file)
                .execute()
            )
            print(results)
            return results

        except HttpError as error:
            print(f"An error occurred: {error}")
            return None

    @tool
    def create_folder(self, name: str):
        """Create a folder and prints the folder ID
        Args:
            name: The name of the folder
        Returns : Folder Id
        """

        try:
            # create drive api client
            file_metadata = {
                "name": name,
                "mimeType": "application/vnd.google-apps.folder",
            }

            # pylint: disable=maybe-no-member
            file = (
                self.service.files().create(body=file_metadata, fields="id").execute()
            )
            print(f'Folder ID: "{file.get("id")}".')
            return file.get("id")

        except HttpError as error:
            print(f"An error occurred: {error}")
            return None

    @tool
    def create_team_drive(self, name: str):
        """Create a drive for team.
        Args:
            name: Name for the team drive
        Returns: ID of the created drive
        """

        try:

            # pylint: disable=maybe-no-member
            team_drive_metadata = {"name": name}
            request_id = str(uuid.uuid4())
            team_drive = (
                self.service.teamdrives()
                .create(body=team_drive_metadata, requestId=request_id, fields="id")
                .execute()
            )
            print(f'Team Drive ID: {team_drive.get("id")}')

        except HttpError as error:
            print(f"An error occurred: {error}")
            team_drive = None

        return team_drive.get("id")

    @tool
    def recover_team_drives(self, real_user):
        """Finds all Team Drives without an organizer and add one
        Args:
            real_user:User ID for the new organizer.
        Returns:
            team drives_object.
        """

        try:

            # pylint: disable=maybe-no-member
            team_drives = []

            page_token = None
            new_organizer_permission = {
                "type": "user",
                "role": "organizer",
                "value": "user@example.com",
            }

            new_organizer_permission["emailAddress"] = real_user

            while True:
                response = (
                    self.service.teamdrives()
                    .list(
                        q="organizerCount = 0",
                        fields="nextPageToken, teamDrives(id, name)",
                        useDomainAdminAccess=True,
                        pageToken=page_token,
                    )
                    .execute()
                )

                for team_drive in response.get("teamDrives", []):
                    print(
                        "Found Team Drive without organizer: {team_drive.get("
                        '"title")},{team_drive.get("id")}'
                    )
                    permission = (
                        self.service.permissions()
                        .create(
                            fileId=team_drive.get("id"),
                            body=new_organizer_permission,
                            useDomainAdminAccess=True,
                            supportsTeamDrives=True,
                            fields="id",
                        )
                        .execute()
                    )
                    print(f'Added organizer permission:{permission.get("id")}')

                team_drives.extend(response.get("teamDrives", []))
                page_token = response.get("nextPageToken", None)
                if page_token is None:
                    break

        except HttpError as error:
            print(f"An error occurred: {error}")
            team_drives = None

        return team_drives
    
    def get_tools(self) -> List:
        """Get the tools in the toolkit."""
        return [
            self.create_drive,
            self.create_folder,
            self.download_file,
            self.create_team_drive,
            self.export_pdf,
            self.duplicate_file,
            self.fetch_appdata_folder,
            self.fetch_changes,
            self.get_file_list,
            self.list_appdata,
            self.move_file_to_folder,
            self.recover_drives,
            self.search_file,
            self.share_file,
            self.upload_to_folder
        ]


# SCOPES = ["https://www.googleapis.com/auth/drive"]
class GoogleSheetTools:
    def __init__(self, creds: Credentials) -> None:
        self.service = build("sheets", "v4", credentials=creds)

    @tool
    def create_sheet(self, title):
        """
        Creates the Sheet the user has access to.
        Args:
            title: The name of the sheet
        Return: Sheet ID
        """
        try:
            spreadsheet = {"properties": {"title": title}}
            spreadsheet = (
                self.service.spreadsheets()
                .create(body=spreadsheet, fields="spreadsheetId")
                .execute()
            )
            print(f"Spreadsheet ID: {(spreadsheet.get('spreadsheetId'))}")
            return spreadsheet.get("spreadsheetId")
        except HttpError as error:
            print(f"An error occurred: {error}")
            return error

    @tool
    def sheet_append_values(
        self, spreadsheet_id, range_name, value_input_option, values
    ):
        """
        Creates the batch_update the user has access to.

        Args:
            spreadsheet_id: Google sheet ID
            range_name: Google sheet range e.g "A1:C2"
            value_input_option: Sheet value option value e.g "USER_ENTERED"
            values: New sheet values e.g [["F", "B"], ["C", "D"]]
        """
        try:
            values = [
                [
                    # Cell values ...
                ],
                # Additional rows ...
            ]
            body = {"values": values}
            result = (
                self.service.spreadsheets()
                .values()
                .append(
                    spreadsheetId=spreadsheet_id,
                    range=range_name,
                    valueInputOption=value_input_option,
                    body=body,
                )
                .execute()
            )
            print(result)
            print(f"{(result.get('updates').get('updatedCells'))} cells appended.")
            return result

        except HttpError as error:
            print(f"An error occurred: {error}")
            return None

    @tool
    def sheet_get_values(self, spreadsheet_id, range_name):
        """Get sheet values
        Args:
            spreadsheet_id: Google sheet ID
            range_name: Sheet range name
        """
        try:
            result = (
                self.service.spreadsheets()
                .values()
                .get(spreadsheetId=spreadsheet_id, range=range_name)
                .execute()
            )
            rows = result.get("values", [])
            print(f"{len(rows)} rows retrieved")
            return result
        except HttpError as error:
            print(f"An error occurred: {error}")
            return error

    @tool
    def sheet_batch_get_values(self, spreadsheet_id, range_names="A1:C2"):
        """
        Get sheet batch values
        Args:
            spreadsheet_id: Google sheet ID
            range_names: Google sheet ranges names
        """
        try:
            range_names = [
                # Range names ...
            ]
            result = (
                self.service.spreadsheets()
                .values()
                .batchGet(spreadsheetId=spreadsheet_id, ranges=range_names)
                .execute()
            )
            ranges = result.get("valueRanges", [])
            print(f"{len(ranges)} ranges retrieved")
            return result
        except HttpError as error:
            print(f"An error occurred: {error}")
            return error

    @tool
    def sheets_batch_update(self, spreadsheet_id, title, find, replacement):
        """
        Update the sheet details in batch, the user has access to.
        Args:
            spreadsheet_id: Google sheet ID
            title: New sheet title
            find: Sheet text to replace
            replacement: Replacement for "find" text
        """

        try:
            requests = []
            # Change the spreadsheet's title.
            requests.append(
                {
                    "updateSpreadsheetProperties": {
                        "properties": {"title": title},
                        "fields": "title",
                    }
                }
            )
            # Find and replace text
            requests.append(
                {
                    "findReplace": {
                        "find": find,
                        "replacement": replacement,
                        "allSheets": True,
                    }
                }
            )
            # Add additional requests (operations) ...

            body = {"requests": requests}
            response = (
                self.service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body=body)
                .execute()
            )
            find_replace_response = response.get("replies")[1].get("findReplace")
            print(
                f"{find_replace_response.get('occurrencesChanged')} replacements made."
            )
            return response

        except HttpError as error:
            print(f"An error occurred: {error}")
            return error

    @tool
    def update_values(self, spreadsheet_id, range_name, value_input_option, values):
        """
        Update sheet values
        Args:
            spreadsheet_id: Google sheet ID
            range_name: Sheet range name e.g "A1:C2"
            value_input_option: Sheet value input option e.g "USER_ENTERED"
            _values: New updated values e.g [["A", "B"], ["C", "D"]]
        """
        try:
            values = [
                [
                    # Cell values ...
                ],
                # Additional rows ...
            ]
            body = {"values": values}
            result = (
                self.service.spreadsheets()
                .values()
                .update(
                    spreadsheetId=spreadsheet_id,
                    range=range_name,
                    valueInputOption=value_input_option,
                    body=body,
                )
                .execute()
            )
            print(f"{result.get('updatedCells')} cells updated.")
            return result
        except HttpError as error:
            print(f"An error occurred: {error}")
            return error

    @tool
    def batch_update_values(
        self, spreadsheet_id, range_name, value_input_option, values
    ):
        """
        Batch update sheet values
        Args:
            spreadsheet_id: Google sheet ID
            range_name: Sheet range name e.g "A1:C2"
            value_input_option: Sheet value input option e.g "USER_ENTERED"
            _values: New updated values e.g [["A", "B"], ["C", "D"]]
        """
        try:
            # values = [
            #     [
            #         # Cell values ...
            #     ],
            #     # Additional rows
            # ]
            data = [
                {"range": range_name, "values": values},
                # Additional ranges to update ...
            ]
            body = {"valueInputOption": value_input_option, "data": data}
            result = (
                self.service.spreadsheets()
                .values()
                .batchUpdate(spreadsheetId=spreadsheet_id, body=body)
                .execute()
            )
            print(f"{(result.get('totalUpdatedCells'))} cells updated.")
            return result
        except HttpError as error:
            print(f"An error occurred: {error}")
            return error

    @tool
    def pivot_tables(self, spreadsheet_id):
        """
        Creates a pivot table from sheet
        Args:
            spreadsheet_id: Google sheet ID
        """
        try:
            body = {"requests": [{"addSheet": {}}, {"addSheet": {}}]}
            batch_update_response = (
                self.service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body=body)
                .execute()
            )
            source_sheet_id = (
                batch_update_response.get("replies")[0]
                .get("addSheet")
                .get("properties")
                .get("sheetId")
            )
            target_sheet_id = (
                batch_update_response.get("replies")[1]
                .get("addSheet")
                .get("properties")
                .get("sheetId")
            )
            requests = []
            requests.append(
                {
                    "updateCells": {
                        "rows": {
                            "values": [
                                {
                                    "pivotTable": {
                                        "source": {
                                            "sheetId": source_sheet_id,
                                            "startRowIndex": 0,
                                            "startColumnIndex": 0,
                                            "endRowIndex": 20,
                                            "endColumnIndex": 7,
                                        },
                                        "rows": [
                                            {
                                                "sourceColumnOffset": 1,
                                                "showTotals": True,
                                                "sortOrder": "ASCENDING",
                                            },
                                        ],
                                        "columns": [
                                            {
                                                "sourceColumnOffset": 4,
                                                "sortOrder": "ASCENDING",
                                                "showTotals": True,
                                            }
                                        ],
                                        "values": [
                                            {
                                                "summarizeFunction": "COUNTA",
                                                "sourceColumnOffset": 4,
                                            }
                                        ],
                                        "valueLayout": "HORIZONTAL",
                                    }
                                }
                            ]
                        },
                        "start": {
                            "sheetId": target_sheet_id,
                            "rowIndex": 0,
                            "columnIndex": 0,
                        },
                        "fields": "pivotTable",
                    }
                }
            )
            body = {"requests": requests}
            response = (
                self.service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body=body)
                .execute()
            )
            return response

        except HttpError as error:
            print(f"An error occurred: {error}")
            return error
    
    def get_tools(self) -> List:
        """Get the tools in the toolkit."""
        return [
            self.create_sheet,
            self.sheet_append_values,
            self.sheet_get_values,
            self.sheet_batch_get_values,
            self.sheets_batch_update,
            self.update_values,
            self.batch_update_values,
            self.pivot_tables
        ]


class GoogleFormTools:
    def __init__(self, creds: Credentials) -> None:
        self.service = build(
            "forms",
            "v1",
            http=creds.authorize(Http()),
            discoveryServiceUrl=settings.DISCOVERY_DOC,
            static_discovery=False,
        )

    @tool
    def create_form(self, name: str):
        """create Google form
        Args:
            name: The name of the form
        """
        try:
            form = {
                "info": {
                    "title": name,
                },
            }
            # Prints the details of the sample form
            result = self.service.forms().create(body=form).execute()
            print(result)
            return result
        except HttpError as error:
            print(f"An error occurred: {error}")
            return None

    @tool
    def retrieve_single_form_response(self, form_id, response_id):
        """Retrieve single Google form response
        Args:
            form_id: Google form ID
            response_id: Google form response ID
        """
        try:
            result = (
                self.service.forms()
                .responses()
                .get(formId=form_id, responseId=response_id)
                .execute()
            )
            print(result)
            return result
        except HttpError as error:
            print(f"An error occurred: {error}")
            return None

    @tool
    def retrieve_all_form_responses(self, form_id):
        """Retrieve all Google form responses
        Args:
            form_id: Google form ID
        """
        try:
            result = self.service.forms().responses().list(formId=form_id).execute()
            print(result)
            return result
        except HttpError as error:
            print(f"An error occurred: {error}")
            return None

    @tool
    def retrieve_form_content(self, form_id):
        """Retrieve Google form content
        Args:
            form_id: Google form ID
        """
        try:
            result = self.service.forms().get(formId=form_id).execute()
            print(result)
            return result
        except HttpError as error:
            print(f"An error occurred: {error}")
            return None

    @tool
    def update_form(self, form_id, description):
        """Update the form with a description
        Args:
            form_id: Google form ID
            description: New description for the form
        """
        try:
            update = {
                "requests": [
                    {
                        "updateFormInfo": {
                            "info": {"description": (description,)},
                            "updateMask": "description",
                        }
                    }
                ]
            }

            # Update the form with a description
            question_setting = (
                self.service.forms().batchUpdate(formId=form_id, body=update).execute()
            )

            # Print the result to see it now has a description
            getresult = self.service.forms().get(formId=form_id).execute()
            print(getresult)
            return getresult
        except HttpError as error:
            print(f"An error occurred: {error}")
            return None

    @tool
    def convert_form_to_quiz(self, form_id):
        """Convert google form to quiz
        Args:
            form_id: Google form ID
        """
        try:
            # JSON to convert the form into a quiz
            update = {
                "requests": [
                    {
                        "updateSettings": {
                            "settings": {"quizSettings": {"isQuiz": True}},
                            "updateMask": "quizSettings.isQuiz",
                        }
                    }
                ]
            }

            # Converts the form into a quiz
            question_setting = (
                self.service.forms().batchUpdate(formId=form_id, body=update).execute()
            )

            # Print the result to see it's now a quiz
            getresult = self.service.forms().get(formId=form_id).execute()
            print(getresult)
            return getresult
        except HttpError as error:
            print(f"An error occurred: {error}")
            return None

    @tool
    def create_form_watch(self, form_id, watch_topic_path):
        """Create google watch for a google form
        Args:
            form_id: Google form ID
            watch_topic_path: Google watch topic path
        """
        try:
            watch = {
                "watch": {
                    "target": {"topic": {"topicName": watch_topic_path}},
                    "eventType": "RESPONSES",
                }
            }

            form_id = "<YOUR_FORM_ID>"

            # Print JSON response after form watch creation
            result = (
                self.service.forms()
                .watches()
                .create(formId=form_id, body=watch)
                .execute()
            )
            print(result)
            return result
        except HttpError as error:
            print(f"An error occurred: {error}")
            return None

    @tool
    def list_form_watches(self, form_id):
        """List google form watches
        Args:
            form_id: Google form ID
        """
        try:
            # Print JSON list of form watches
            result = self.service.forms().watches().list(formId=form_id).execute()
            print(result)
            return result
        except HttpError as error:
            print(f"An error occurred: {error}")
            return f"An error occurred: {error}"

    @tool
    def renew_form_watch(self, form_id, watch_id):
        """Renew google form watch
        Args:
            form_id: Google form ID
            watch_id: Google watch ID
        """
        try:
            # Print JSON response after renewing a form watch
            result = (
                self.service.forms()
                .watches()
                .renew(formId=form_id, watchId=watch_id)
                .execute()
            )
            print(result)
            return result
        except HttpError as error:
            print(f"An error occurred: {error}")
            return f"An error occurred: {error}"

    @tool
    def delete_form_watch(self, form_id, watch_id):
        """Delete google form watch
        Args:
            form_id: Google form ID
            watch_id: Google watch ID
        """
        try:
            # Print JSON response after deleting a form watch
            result = (
                self.service.forms()
                .watches()
                .delete(formId=form_id, watchId=watch_id)
                .execute()
            )
            print(result)
            return result
        except HttpError as error:
            print(f"An error occurred: {error}")
            return f"An error occurred: {error}"


class SalesForceTools:
    def __init__(self, username, password, security_token, instance, session_id='') -> None:
        self.sf = Salesforce(instance=instance, session_id=session_id)
        self.sf = Salesforce(username=username, password=password, security_token=security_token)

    @tool
    def search_knowledge(self, query: str) -> str:
        """
        Searches Salesforce Knowledge articles for a given query using SOSL, within the LangChain framework.

        Parameters:
            query (str): The keyword or phrase to search for within Salesforce Knowledge articles.
        
        Returns:
            str: A formatted string containing the titles, questions, and URLs of the found articles, dynamically constructed based on the Salesforce instance.
        """
        # Assuming 'sf' Salesforce connection object is initialized and accessible globally

        print (f"Searching Salesforce Knowledge for: {query}")
        # Format the SOSL search string with the search term enclosed in braces
        search_string = "FIND {{{0}}} IN ALL FIELDS RETURNING Knowledge__kav(Id, Title, Question__c, Answer__c, UrlName)".format(query)
        print (f"search_string: {search_string}")
        search_result = self.sf.search(search_string)
        
        # Initialize an empty list to store formatted article details
        articles_details = []

        # Dynamically construct the base URL from the Salesforce instance URL
        base_url = self.sf.base_url.split('/services')[0]

        # Process search results
        for article in search_result['searchRecords']:
            # Dynamically construct the URL for the article using the Salesforce instance URL
            article_id = article['Id']
            article_url = f"{base_url}/lightning/r/Knowledge__kav/{article_id}/view"
            article_details = f"Title: {article['Title']}, Question: {article['Question__c']}, AnswerL:{article['Answer__c']}, URL: {article_url}"
            articles_details.append(article_details)

        print(articles_details)

        # Join all article details into a single string to return
        return "\n".join(articles_details)
    
    @tool
    def search_opportunities(self, query: str) -> str:
        """
        Searches Salesforce opportunities for a given query using SOSL, within the LangChain framework.

        Parameters:
            query (str): The keyword or phrase to search for within Salesforce opportunities.
        
        Returns:
            str: A formatted string containing the details of the found opportunities, dynamically constructed based on the Salesforce instance.
        """
        # Assuming 'sf' Salesforce connection object is initialized and accessible globally

        print(f"Searching Salesforce opportunities for: {query}")
        # Format the SOSL search string with the search term enclosed in braces
        search_string = "FIND {{{0}}} IN ALL FIELDS RETURNING Opportunity(Id, Name, CloseDate, Amount, StageName, )".format(query)
        print(f"search_string: {search_string}")
        search_result = self.sf.search(search_string)

        # Initialize an empty list to store formatted opportunity details
        opportunities_details = []

        # Process search results
        for opportunity in search_result['searchRecords']:
            # Construct opportunity details
            opportunity_details = f"Opportunity: {opportunity['Name']}, Close Date: {opportunity['CloseDate']}, Amount: {opportunity['Amount']}, Stage: {opportunity['StageName']},"
            opportunities_details.append(opportunity_details)

        print(opportunities_details)

        # Join all opportunity details into a single string to return
        return "\n".join(opportunities_details)

    @tool
    def create_case(self, subject: str, description: str) -> str:
        """
        Creates a case record in Salesforce using the provided subject and description.

        Parameters:
            subject (str): The subject of the case.
            description (str): The description of the case.
        
        Returns:
            str: A confirmation message indicating whether the case was successfully created or not, along with a link to the created case.
        """
        try:
            # Create a dictionary with case details
            case_details = {
                'Subject': subject,
                'Description': description,
                'Origin': 'Web'  # Set the default case origin to "Web"
            }
            
            # Create the case record in Salesforce
            new_case = self.sf.Case.create(case_details)
            
            # Extract the Case Id from the newly created case record
            case_id = new_case['id']
            
            # Construct the link to the created case
            case_link = f"{self.sf.base_url}/lightning/r/Case/{case_id}/view"
            
            # Return success message along with the link to the created case
            return f"Case created successfully. Case Link: {case_link}"
        
        except Exception as e:
            # Return error message if case creation fails
            return f"Error creating case: {str(e)}"


    @tool
    def search_account_summary(self, account_name: str) -> str:
        """
        Searches for Opportunities, Contacts, and Cases associated with the provided Account name.

        Parameters:
            account_name (str): The name of the Account to search for.

        Returns:
            str: A formatted summary containing information about Opportunities, Contacts, and Cases.
        """
        try:
            # Step 1: Search for the Account based on the provided name
            search_result = self.sf.query(f"SELECT Id, Name FROM Account WHERE Name LIKE '%{account_name}%' LIMIT 1")
            if search_result['totalSize'] == 0:
                return f"No Account found with a similar name to '{account_name}'."

            # Extract Account Id from the search result
            account_id = search_result['records'][0]['Id']

            # Step 2: Retrieve associated Opportunities, Contacts, and Cases
            opportunities = self.sf.query_all(f"SELECT Id, Name, Amount, StageName FROM Opportunity WHERE AccountId = '{account_id}'")
            contacts = self.sf.query_all(f"SELECT Id, Name FROM Contact WHERE AccountId = '{account_id}'")
            cases = self.sf.query_all(f"SELECT Id, CaseNumber, Subject, Description FROM Case WHERE AccountId = '{account_id}'")

            # Format the summary
            summary = f"Account Summary for '{account_name}':\n\n"

            # Add information about Opportunities
            if opportunities['totalSize'] > 0:
                summary += "Opportunities:\n"
                for opp in opportunities['records']:
                    summary += f"- Opportunity: {opp['Name']}, Amount: {opp.get('Amount', 'N/A')}, Stage: {opp.get('StageName', 'N/A')}\n"
            else:
                summary += "No Opportunities found.\n"

            # Add information about Contacts
            if contacts['totalSize'] > 0:
                summary += "\nContacts:\n"
                for contact in contacts['records']:
                    summary += f"- Contact: {contact['Name']}\n"
            else:
                summary += "No Contacts found.\n"

            # Add information about Cases
            if cases['totalSize'] > 0:
                summary += "\nCases:\n"
                for case in cases['records']:
                    summary += f"- Case Number: {case['CaseNumber']}, Subject: {case.get('Subject', 'N/A')}, Description: {case.get('Description', 'N/A')}\n"
            else:
                summary += "No Cases found.\n"

            return summary

        except Exception as e:
            return f"Error searching for Account summary: {str(e)}"
    
    def get_tools():
        return []