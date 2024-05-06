from typing import Type
from langchain_core.pydantic_v1 import BaseModel, Field

from agents.utils.tools.base import BaseTool


class MoveFileSchema(BaseModel):
    """Input for MoveFileTool"""

    file_id: str = Field(
        ...,
        description="The file ID",
    )

    folder_id: str = Field(
        ...,
        description="The folder ID",
    )


class GoogleDriveMoveFile(BaseTool):
    """Tool that move file to a specific folder in google drive."""

    name: str = "move_file"
    description: str = (
        "Use this tool to move file to a folder in google drive."
    )
    args_schema: Type[MoveFileSchema] = MoveFileSchema

    def _run(self, file_id: str, folder_id: str):
        """move file in google drive"""
        # Call the Drive v3 API
        try:
            file = self.service.files().get(fileId=file_id, fields="parents").execute()
            previous_parents = ",".join(file.get("parents"))
            # Move the file to the new folder
            file = (
                self.api_resource.files()
                .update(
                    fileId=file_id,
                    addParents=folder_id,
                    removeParents=previous_parents,
                    fields="id, parents",
                )
                .execute()
            )
            return file.get("parents")
        except Exception as e:
            raise Exception(f"An error occurred: {e}")