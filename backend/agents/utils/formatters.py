from typing import Any
from langchain.pydantic_v1 import BaseModel, Field


class Input(BaseModel):
    input: str


class Output(BaseModel):
    output: Any