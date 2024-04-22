import datetime
import io
from typing import List
import uuid
from django.conf import settings
from httplib2 import Http
from langchain.tools import tool

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload


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
