import datetime
from typing import Type
from langchain_core.pydantic_v1 import BaseModel, Field

from agents.utils.tools.base import BaseTool


class EventListSchema(BaseModel):
    """Input for EventListTool"""

    calender_id: str = Field(
        ...,
        description="The calender ID to list",
    )

    time: datetime.datetime = Field(
        ...,
        description="The minimum time of event",
    )

    max_result: int = Field(
        ...,
        description="The maximum number of events to list",
    )


class CalenderEventList(BaseTool):
    """Tool that list a number of events in Google Calender."""

    name: str = "calender_event_list"
    description: str = (
        "Use this tool to list a number of events in Google calender."
    )
    args_schema: Type[EventListSchema] = EventListSchema

    def _run(
        self,
        calender_id: str = "primary",
        time: datetime.datetime = datetime.datetime.now(datetime.UTC).isoformat() + "Z",
        max_result: int = 10,
    ):
        """Get list of calender events in google calender"""
        print("Getting the upcoming 10 events")
        try:
            events_result = (
                self.api_resource.events()
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
        except Exception as e:
            raise Exception(f"An error occurred: {e}")