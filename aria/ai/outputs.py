from pydantic import BaseModel, Field


class ImprovedPromptResponse(BaseModel):
    original: str = Field(
        ...,
        description="The original prompt to be improved",
    )
    improved: str = Field(
        ...,
        description="The improved prompt based on the original prompt",
    )
    explanation: str = Field(
        ...,
        description="The explanation for how the original prompt was improved",
    )
