from typing import Any, Type
from langchain_core.pydantic_v1 import BaseModel, Field

from agents.utils.tools.base import BaseTool


class GoogleDriveFetchFolders(BaseTool):
    """Tool that fetch appdata folder in google drive."""

    name: str = "fetch_appdata_folder"
    description: str = (
        "Use this tool to fetch appdata folder in google drive."
    )
    args_schema: Type[Any] = None

    def _run(self):
        """fetch appdata folder in google drive"""
        # Call the Drive v3 API
        try:
            file = (
                self.api_resource.files().get(fileId="appDataFolder", fields="id").execute()
            )
            print(f'Folder ID: {file.get("id")}')
            return file.id
        except Exception as e:
            raise Exception(f"An error occurred: {e}")