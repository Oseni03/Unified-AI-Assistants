from typing import Type
from langchain_core.pydantic_v1 import BaseModel, Field

from agents.utils.tools.base import BaseTool


class SearchFileSchema(BaseModel):
    """Input for SearchFileTool"""

    mimetype: str = Field(
        ...,
        description="The mimetype of the file",
    )


class GoogleDriveSearchFile(BaseTool):
    """Tool that search for file in google drive."""

    name: str = "search_file"
    description: str = (
        "Use this tool to to search file in google drive."
    )
    args_schema: Type[SearchFileSchema] = SearchFileSchema

    def _run(self, mimetype: str = "image/jpeg"):
        """search file in google drive"""
        # Call the Drive v3 API
        try:
            files = []
            page_token = None
            while True:
                # pylint: disable=maybe-no-member
                response = (
                    self.api_resource.files()
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
            return files
        except Exception as e:
            raise Exception(f"An error occurred: {e}")