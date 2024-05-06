import datetime
from typing import Type
from langchain_core.pydantic_v1 import BaseModel, Field

from agents.utils.tools.base import BaseTool


class FileListSchema(BaseModel):
    """Input for EventListTool"""

    page_size: int = Field(
        ...,
        description="The size of the page",
    )


class GoogleDriveFileList(BaseTool):
    """Tool that list of files in google drive."""

    name: str = "file_list"
    description: str = (
        "Use this tool to list the files in google drive."
    )
    args_schema: Type[FileListSchema] = FileListSchema

    def _run(self, page_size: int = 10):
        """get list of files in google drive"""
        # Call the Drive v3 API
        try:
            results = (
                self.api_resource.files()
                .list(page_size=page_size, fields="nextPageToken, files(id, name)")
                .execute()
            )
            items = results.get("files", [])
            return items
        except Exception as e:
            raise Exception(f"An error occurred: {e}")