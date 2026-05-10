"""Explicit Pydantic schemas for all remaining tools.

llama-index's auto-schema generation does NOT extract descriptions from
docstrings.  Every parameter must carry a ``Field(description=...)`` so
the LLM understands what to pass.  This file centralises schemas for
tools whose modules haven't been updated yet.
"""

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Tier 2 — auxiliary tools (plan, scratchpad, process)
# ---------------------------------------------------------------------------


class PlanSchema(BaseModel):
    """Schema exposed to the LLM for the plan tool."""

    reason: str = Field(
        description="Required. Brief explanation of why you are calling this tool."
    )
    action: str = Field(
        description=(
            "Action: 'create' (new plan), 'add_step', 'update_step', "
            "'execute_step', 'complete_step', 'fail_step', "
            "'skip_step', 'update', 'summary', 'delete', 'list', 'status'."
        )
    )
    task: str | None = Field(
        default=None,
        description="Task description (required for 'create').",
    )
    steps: list[str] | None = Field(
        default=None,
        description="List of step descriptions (optional for 'create').",
    )
    step_id: str | None = Field(
        default=None,
        description="Step ID to target (required for step actions).",
    )
    status: str | None = Field(
        default=None,
        description="Status to set: 'pending', 'in_progress', 'completed', 'failed', 'skipped'.",
    )
    result: str | None = Field(
        default=None,
        description="Result text for a step (used with 'update_step').",
    )
    description: str | None = Field(
        default=None,
        description="Updated description (used with 'update_step').",
    )
    after_step_id: str | None = Field(
        default=None,
        description="Insert a new step after this step ID (for 'add_step').",
    )
    step_ids: list[str] | None = Field(
        default=None,
        description="List of step IDs (used with 'execute_step' for batch).",
    )
    execution_id: str | None = Field(
        default=None,
        description="Execution ID for tracking batch operations.",
    )
    agent_id: str = Field(
        default="default",
        description="Auto-set. Do not provide.",
    )


class ScratchpadSchema(BaseModel):
    """Schema exposed to the LLM for the scratchpad tool."""

    reason: str = Field(
        description="Required. Brief explanation of why you are using the scratchpad."
    )
    key: str = Field(
        description="Unique key to identify this scratchpad entry.",
    )
    value: str | None = Field(
        default=None,
        description="Value to store (required for 'set' and 'append' operations).",
    )
    operation: str = Field(
        default="get",
        description=(
            "Operation: 'get' (read), 'set' (create/update), "
            "'append' (add to existing), 'delete', 'list'."
        ),
    )
    agent_id: str = Field(
        default="aria",
        description="Auto-set. Do not provide.",
    )


class ProcessSchema(BaseModel):
    """Schema exposed to the LLM for the process tool."""

    reason: str = Field(
        description="Required. Brief explanation of why you are managing this process."
    )
    action: str = Field(
        description=(
            "Action: 'start' (launch new process), 'stop', 'status', "
            "'logs', 'list', 'restart', 'signal'."
        )
    )
    name: str | None = Field(
        default=None,
        description="Process name for identification (used with 'start').",
    )
    command: str | None = Field(
        default=None,
        description="Command to execute (required for 'start').",
    )
    args: list[str] | None = Field(
        default=None,
        description="Command arguments as a list of strings.",
    )
    timeout: int | None = Field(
        default=None,
        description="Timeout in seconds before auto-killing the process.",
    )
    working_dir: str | None = Field(
        default=None,
        description="Working directory for the process.",
    )
    env: dict[str, str] | None = Field(
        default=None,
        description="Additional environment variables for the process.",
    )
    use_shell: bool = Field(
        default=False,
        description="If true, execute via system shell (allows pipes, redirects).",
    )
    signal_name: str | None = Field(
        default=None,
        description="Signal name for 'signal' action (e.g. 'SIGTERM', 'SIGKILL').",
    )


# ---------------------------------------------------------------------------
# Tier 3 — on-demand tools
# ---------------------------------------------------------------------------


class HttpRequestSchema(BaseModel):
    """Schema exposed to the LLM for http_request."""

    reason: str = Field(
        description="Required. Brief explanation of why you are making this request."
    )
    method: str = Field(
        description="HTTP method: 'GET', 'POST', 'PUT', 'DELETE', 'PATCH', etc.",
    )
    url: str = Field(description="Full URL to send the request to.")
    headers: dict[str, str] | None = Field(
        default=None,
        description="HTTP headers as key-value pairs.",
    )
    body: str | None = Field(
        default=None,
        description="Request body (for POST/PUT/PATCH). String or JSON.",
    )
    timeout: int | None = Field(
        default=None,
        description="Request timeout in seconds.",
    )


class PythonSchema(BaseModel):
    """Schema exposed to the LLM for the python sandbox."""

    reason: str = Field(
        description="Required. Brief explanation of why you are running this code."
    )
    code: str | None = Field(
        default=None,
        description="Python code to execute.",
    )
    file: str | None = Field(
        default=None,
        description="Absolute path to a Python file to execute.",
    )
    args: list[str] | None = Field(
        default=None,
        description="Command-line arguments to pass to the script.",
    )
    timeout: int | None = Field(
        default=30,
        description="Execution timeout in seconds (default: 30).",
    )
    check_only: bool = Field(
        default=False,
        description="If true, only check syntax without executing.",
    )


class CopyFileSchema(BaseModel):
    """Schema exposed to the LLM for copy_file."""

    reason: str = Field(
        description="Required. Brief explanation of why you are copying this file."
    )
    source: str = Field(
        description="Absolute path to the source file.",
    )
    destination: str = Field(
        description="Absolute path to the destination.",
    )
    overwrite: bool | None = Field(
        default=False,
        description="If true, overwrite existing destination file (default: false).",
    )


class FetchStockPriceSchema(BaseModel):
    """Schema exposed to the LLM for fetch_current_stock_price."""

    reason: str = Field(
        description="Required. Brief explanation of why you need this price."
    )
    ticker: str = Field(
        description="Stock ticker symbol (e.g. 'AAPL', 'MSFT', 'GOOGL').",
    )


class FetchCompanyInfoSchema(BaseModel):
    """Schema exposed to the LLM for fetch_company_information."""

    reason: str = Field(
        description="Required. Brief explanation of why you need this information."
    )
    ticker: str = Field(
        description="Stock ticker symbol (e.g. 'AAPL', 'MSFT').",
    )


class FetchTickerNewsSchema(BaseModel):
    """Schema exposed to the LLM for fetch_ticker_news."""

    reason: str = Field(
        description="Required. Brief explanation of why you need this news."
    )
    ticker: str = Field(description="Stock ticker symbol.")
    max_articles: int = Field(
        default=10,
        description="Maximum number of articles to return (default: 10).",
    )


class SearchImdbTitlesSchema(BaseModel):
    """Schema exposed to the LLM for search_imdb_titles."""

    reason: str = Field(
        description="Required. Brief explanation of why you are searching."
    )
    query: str = Field(description="Search query for movies, shows, or people.")
    title_type: str | None = Field(
        default=None,
        description=(
            "Filter by type: 'movie', 'tvSeries', 'tvMiniSeries', "
            "'tvMovie', 'videoGame', etc."
        ),
    )


class GetMovieDetailsSchema(BaseModel):
    """Schema exposed to the LLM for get_movie_details."""

    reason: str = Field(
        description="Required. Brief explanation of why you need these details."
    )
    imdb_id: str = Field(
        description="IMDb ID (e.g. 'tt0111161' for The Shawshank Redemption)."
    )


class GetPersonDetailsSchema(BaseModel):
    """Schema exposed to the LLM for get_person_details."""

    reason: str = Field(
        description="Required. Brief explanation of why you need these details."
    )
    person_id: str = Field(description="IMDb person ID (e.g. 'nm0000206').")


class GetPersonFilmographySchema(BaseModel):
    """Schema exposed to the LLM for get_person_filmography."""

    reason: str = Field(
        description="Required. Brief explanation of why you need this filmography."
    )
    person_id: str = Field(description="IMDb person ID (e.g. 'nm0000206').")


class GetAllSeriesEpisodesSchema(BaseModel):
    """Schema exposed to the LLM for get_all_series_episodes."""

    reason: str = Field(
        description="Required. Brief explanation of why you need episode data."
    )
    imdb_id: str = Field(
        description="IMDb series ID (e.g. 'tt0944947' for Game of Thrones)."
    )


class GetMovieReviewsSchema(BaseModel):
    """Schema exposed to the LLM for get_movie_reviews."""

    reason: str = Field(
        description="Required. Brief explanation of why you need reviews."
    )
    imdb_id: str = Field(description="IMDb movie ID (e.g. 'tt0111161').")


class GetMovieTriviaSchema(BaseModel):
    """Schema exposed to the LLM for get_movie_trivia."""

    reason: str = Field(
        description="Required. Brief explanation of why you need trivia."
    )
    imdb_id: str = Field(description="IMDb movie ID (e.g. 'tt0111161').")


class GetYoutubeTranscriptionSchema(BaseModel):
    """Schema exposed to the LLM for get_youtube_video_transcription."""

    reason: str = Field(
        description="Required. Brief explanation of why you need this transcription."
    )
    url: str = Field(description="Full YouTube video URL.")
    languages: list[str] | None = Field(
        default=None,
        description="Preferred languages in order (e.g. ['en', 'es']). Default: English.",
    )
