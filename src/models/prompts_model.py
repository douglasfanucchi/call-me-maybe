"""Pydantic models for the prompts input file."""

from pydantic import BaseModel, RootModel


class PromptModel(BaseModel):
    """A single natural-language request.

    Attributes:
        prompt: The text written by the user.
    """

    prompt: str


class PromptsModel(RootModel[list[PromptModel]]):
    """List of prompts.

    It validates a JSON file whose top level is an array. The validated
    list is available in the ``root`` attribute.
    """

    ...
