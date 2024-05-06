from typing import Type
import uuid
from langchain_core.pydantic_v1 import BaseModel, Field

from agents.utils.tools.base import BaseTool


class CreateDriveSchema(BaseModel):
    """Input for CreateDriveTool"""

    name: str = Field(
        ...,
        description="The name of the drive",
    )


class GoogleDriveCeateDrive(BaseTool):
    """Tool that create drive in google drive."""

    name: str = "create_drive"
    description: str = (
        "Use this tool to to create google drive."
    )
    args_schema: Type[CreateDriveSchema] = CreateDriveSchema

    def _run(self, name: str):
        """create google drive"""
        # Call the Drive v3 API
        try:
            drive_metadata = {"name": name}
            request_id = str(uuid.uuid4())
            # pylint: disable=maybe-no-member
            drive = (
                self.api_resource.drives()
                .create(body=drive_metadata, requestId=request_id, fields="id")
                .execute()
            )
            print(f'Drive ID: {drive.get("id")}')
            drive["name"] = name
            return drive
        except Exception as e:
            raise Exception(f"An error occurred: {e}")