import uuid
from typing import List, Optional, Type
from langchain_core.pydantic_v1 import BaseModel, Field

from agents.utils.tools.base import BaseTool
from googleapiclient.http import MediaFileUpload


class CreateDriveUploadSchema(BaseModel):
    """Input for UploadFile"""

    file_name: str = Field(
        ...,
        description="The name of the file",
    )
    
    mimetype: str = Field(
        ...,
        description="The mimetype of the file",
    )

    folder_id: Optional[str] = Field(
        None,
        description="The ID of the folder to upload to",
    )


class GoogleDriveUploadFile(BaseTool):
    """Tool that upload file to a folder in google drive."""

    name: str = "upload_file_to_folder"
    description: str = (
        "Use this tool to upload file to a folder in google drive."
    )
    args_schema: Type[CreateDriveUploadSchema] = CreateDriveUploadSchema

    def _run(self, file_name: str, mimetype: str, folder_id: str=None):
        """upload file to folder in google drive"""
        # Call the Drive v3 API
        try:
            if folder_id:
                parent_folder = [folder_id]
            else:
                parent_folder = ["appDataFolder"]

            file_metadata = {"name": file_name, "parents": parent_folder}
            media = MediaFileUpload(file_name, mimetype=mimetype, resumable=True)
            file = (
                self.api_resource.files()
                .create(body=file_metadata, media_body=media, fields="id")
                .execute()
            )
            print(f'File ID: {file.get("id")}')
            return file.get("id")
        except Exception as e:
            raise Exception(f"An error occurred: {e}")