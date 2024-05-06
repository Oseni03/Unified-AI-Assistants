from typing import Any, Type
from langchain_core.pydantic_v1 import BaseModel, Field

from agents.utils.tools.base import BaseTool


class GoogleDriveListAppData(BaseTool):
    """Tool that List all files inserted in the application data folder in google drive."""

    name: str = "fetch_appdata_folder"
    description: str = (
        "Use this tool list all files inserted in the apllication data folder in google drive."
    )
    args_schema: Type[Any] = None

    def _run(self):
        """"List all files inserted in the application data folder
        prints file titles with Ids."""
        # Call the Drive v3 API
        try:
            response = (
                self.api_resource.files()
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
            return response.get("files")
        except Exception as e:
            raise Exception(f"An error occurred: {e}")