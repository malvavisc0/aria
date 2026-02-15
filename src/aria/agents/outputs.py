from pydantic import BaseModel, Field


class ResearchReport(BaseModel):
    """
    A comprehensive data model representing the structured metadata and
    summary of a completed research task. Use this to catalog reports
    before they are persisted to long-term storage.
    """

    title: str = Field(description="The title of the report")

    file_name: str = Field(description="The name of the file report.")

    file_path: str = Field(description="The file path where the report is saved.")

    file_size: int = Field(
        ge=0,
        description="The size of the final report file in bytes.",
    )
    brief: str = Field(
        description="A concise executive summary (2-3 sentences) of the research results for quick review."
    )

    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="A confidence score from 0.0 to 1.0 reflecting the quality and availability of the source material.",
    )
