from typing import Any, Type
from langchain_core.pydantic_v1 import BaseModel, Field

from agents.utils.tools.base import BaseTool


class GoogleDriveFetchChanges(BaseTool):
    """Tool that fetch changes in google drive."""

    name: str = "fetch_changes"
    description: str = (
        "Use this tool to fetch changes in google drive."
    )
    args_schema: Type[Any] = None

    def _run(self):
        """fetch changes in google drive"""
        # Call the Drive v3 API
        try:
            # Begin with our last saved start token for this user or the
            # current token from getStartPageToken()
            page_token = (
                self.api_resource.changes()
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
            return changes
        except Exception as e:
            raise Exception(f"An error occurred: {e}")