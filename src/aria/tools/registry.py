"""Tool registry for categorized tool loading.

Categories:
- core_lite: Aria agent tools (reasoning, shell)
- files_lite: Aria agent file tools (read_file, write_file, edit_file,
              list_files, search_files)
- core: Worker tools (reasoning, plan, scratchpad, shell)
- files: Worker file tools (read_file, write_file, edit_file,
         file_info, list_files, search_files, copy_file)
- web: On-demand browser tools
- development: On-demand python tool
- finance: On-demand stock tools
- entertainment: On-demand imdb tools
- system: On-demand http_request, process
"""

from collections.abc import Callable
from typing import Dict, List, Optional

from llama_index.core.tools import FunctionTool
from loguru import logger

# Tool categories
CORE_LITE = "core_lite"
FILES_LITE = "files_lite"
CORE = "core"
FILES = "files"
AX = "ax"
WEB = "web"
DEVELOPMENT = "development"
FINANCE = "finance"
ENTERTAINMENT = "entertainment"
SYSTEM = "system"

ALL_CATEGORIES = [
    CORE,
    FILES,
    AX,
    WEB,
    DEVELOPMENT,
    FINANCE,
    ENTERTAINMENT,
    SYSTEM,
]


def _import_function(module_path: str, function_name: str) -> Callable:
    """Import a function from a module path."""
    import importlib

    module = importlib.import_module(module_path)
    return getattr(module, function_name)


def _get_core_lite_tools() -> list[FunctionTool]:
    """Aria agent core tools: reasoning + shell only."""
    from aria.tools.reasoning.functions import ReasoningSchema
    from aria.tools.shell.functions import ShellToolSchema

    tool_specs = [
        ("aria.tools.reasoning", "reasoning"),
        ("aria.tools.shell", "shell"),
    ]
    explicit_schemas = {
        "reasoning": ReasoningSchema,
        "shell": ShellToolSchema,
    }
    tools: list[FunctionTool] = []
    for mod, fn in tool_specs:
        func = _import_function(mod, fn)
        schema = explicit_schemas.get(fn)
        if schema is not None:
            tools.append(FunctionTool.from_defaults(fn=func, fn_schema=schema))
        else:
            tools.append(FunctionTool.from_defaults(fn=func))
    return tools


def _get_file_lite_tools() -> list[FunctionTool]:
    """Aria agent file tools: no file_info or copy_file."""
    from aria.tools.files.unified_read import (
        ListFilesSchema,
        ReadFileSchema,
        SearchFilesSchema,
    )
    from aria.tools.files.write_operations import (
        EditFileSchema,
        WriteFileSchema,
    )

    tool_specs = [
        ("aria.tools.files", "read_file"),
        ("aria.tools.files", "write_file"),
        ("aria.tools.files", "edit_file"),
        ("aria.tools.files", "list_files"),
        ("aria.tools.files", "search_files"),
    ]
    explicit_schemas = {
        "read_file": ReadFileSchema,
        "write_file": WriteFileSchema,
        "edit_file": EditFileSchema,
        "list_files": ListFilesSchema,
        "search_files": SearchFilesSchema,
    }
    tools: list[FunctionTool] = []
    for mod, fn in tool_specs:
        func = _import_function(mod, fn)
        schema = explicit_schemas.get(fn)
        if schema is not None:
            tools.append(FunctionTool.from_defaults(fn=func, fn_schema=schema))
        else:
            tools.append(FunctionTool.from_defaults(fn=func))
    return tools


def _get_core_tools() -> list[FunctionTool]:
    """Worker core tools: reasoning, plan, scratchpad, shell."""
    from aria.tools.reasoning.functions import ReasoningSchema
    from aria.tools.schemas import PlanSchema, ScratchpadSchema
    from aria.tools.shell.functions import ShellToolSchema

    tool_specs = [
        ("aria.tools.reasoning", "reasoning"),
        ("aria.tools.planner", "plan"),
        ("aria.tools.scratchpad", "scratchpad"),
        ("aria.tools.shell", "shell"),
    ]
    explicit_schemas = {
        "reasoning": ReasoningSchema,
        "plan": PlanSchema,
        "scratchpad": ScratchpadSchema,
        "shell": ShellToolSchema,
    }
    tools: list[FunctionTool] = []
    for mod, fn in tool_specs:
        func = _import_function(mod, fn)
        schema = explicit_schemas.get(fn)
        if schema is not None:
            tools.append(FunctionTool.from_defaults(fn=func, fn_schema=schema))
        else:
            tools.append(FunctionTool.from_defaults(fn=func))
    return tools


def _get_file_tools() -> list[FunctionTool]:
    """Worker file tools: full set including file_info and copy_file."""
    from aria.tools.files.unified_read import (
        FileInfoSchema,
        ListFilesSchema,
        ReadFileSchema,
        SearchFilesSchema,
    )
    from aria.tools.files.write_operations import (
        EditFileSchema,
        WriteFileSchema,
    )
    from aria.tools.schemas import CopyFileSchema

    tool_specs = [
        ("aria.tools.files", "read_file"),
        ("aria.tools.files", "write_file"),
        ("aria.tools.files", "edit_file"),
        ("aria.tools.files", "file_info"),
        ("aria.tools.files", "list_files"),
        ("aria.tools.files", "search_files"),
        ("aria.tools.files", "copy_file"),
    ]
    explicit_schemas = {
        "read_file": ReadFileSchema,
        "write_file": WriteFileSchema,
        "edit_file": EditFileSchema,
        "file_info": FileInfoSchema,
        "list_files": ListFilesSchema,
        "search_files": SearchFilesSchema,
        "copy_file": CopyFileSchema,
    }
    tools: list[FunctionTool] = []
    for mod, fn in tool_specs:
        func = _import_function(mod, fn)
        schema = explicit_schemas.get(fn)
        if schema is not None:
            tools.append(FunctionTool.from_defaults(fn=func, fn_schema=schema))
        else:
            tools.append(FunctionTool.from_defaults(fn=func))
    return tools


def _get_web_tools() -> list[FunctionTool]:
    """Get on-demand browser tools."""
    try:
        from aria.config.api import Lightpanda

        if not Lightpanda.is_available():
            logger.debug("Browser tools not available (Lightpanda)")
            return []
    except Exception:
        return []

    from aria.tools.browser.functions import BrowserClickSchema, OpenUrlSchema

    tool_specs = [
        ("aria.tools.browser", "open_url"),
        ("aria.tools.browser", "browser_click"),
    ]
    explicit_schemas = {
        "open_url": OpenUrlSchema,
        "browser_click": BrowserClickSchema,
    }
    tools = []
    for mod, fn in tool_specs:
        try:
            func = _import_function(mod, fn)
            schema = explicit_schemas.get(fn)
            if schema is not None:
                tools.append(
                    FunctionTool.from_defaults(async_fn=func, fn_schema=schema)
                )
            else:
                tools.append(FunctionTool.from_defaults(async_fn=func))
        except (ImportError, AttributeError):
            logger.warning(f"Could not load browser tool: {mod}.{fn}")
    return tools


def _get_development_tools() -> list[FunctionTool]:
    """Get on-demand development tools."""
    from aria.tools.schemas import PythonSchema

    func = _import_function("aria.tools.development", "python")
    return [FunctionTool.from_defaults(fn=func, fn_schema=PythonSchema)]


def _get_finance_tools() -> list[FunctionTool]:
    """Get on-demand finance tools."""
    from aria.tools.schemas import (
        FetchCompanyInfoSchema,
        FetchStockPriceSchema,
        FetchTickerNewsSchema,
    )

    tool_specs = [
        ("aria.tools.search", "fetch_current_stock_price"),
        ("aria.tools.search", "fetch_company_information"),
        ("aria.tools.search", "fetch_ticker_news"),
    ]
    explicit_schemas = {
        "fetch_current_stock_price": FetchStockPriceSchema,
        "fetch_company_information": FetchCompanyInfoSchema,
        "fetch_ticker_news": FetchTickerNewsSchema,
    }
    tools: list[FunctionTool] = []
    for mod, fn in tool_specs:
        func = _import_function(mod, fn)
        schema = explicit_schemas.get(fn)
        if schema is not None:
            tools.append(FunctionTool.from_defaults(fn=func, fn_schema=schema))
        else:
            tools.append(FunctionTool.from_defaults(fn=func))
    return tools


def _get_entertainment_tools() -> list[FunctionTool]:
    """Get on-demand entertainment tools."""
    from aria.tools.schemas import (
        GetAllSeriesEpisodesSchema,
        GetMovieDetailsSchema,
        GetMovieReviewsSchema,
        GetMovieTriviaSchema,
        GetPersonDetailsSchema,
        GetPersonFilmographySchema,
        GetYoutubeTranscriptionSchema,
        SearchImdbTitlesSchema,
    )

    tool_specs = [
        ("aria.tools.imdb", "search_imdb_titles"),
        ("aria.tools.imdb", "get_movie_details"),
        ("aria.tools.imdb", "get_person_details"),
        ("aria.tools.imdb", "get_person_filmography"),
        ("aria.tools.imdb", "get_all_series_episodes"),
        ("aria.tools.imdb", "get_movie_reviews"),
        ("aria.tools.imdb", "get_movie_trivia"),
        ("aria.tools.search", "get_youtube_video_transcription"),
    ]
    explicit_schemas = {
        "search_imdb_titles": SearchImdbTitlesSchema,
        "get_movie_details": GetMovieDetailsSchema,
        "get_person_details": GetPersonDetailsSchema,
        "get_person_filmography": GetPersonFilmographySchema,
        "get_all_series_episodes": GetAllSeriesEpisodesSchema,
        "get_movie_reviews": GetMovieReviewsSchema,
        "get_movie_trivia": GetMovieTriviaSchema,
        "get_youtube_video_transcription": GetYoutubeTranscriptionSchema,
    }
    tools = []
    for mod, fn in tool_specs:
        try:
            func = _import_function(mod, fn)
            schema = explicit_schemas.get(fn)
            if schema is not None:
                tools.append(FunctionTool.from_defaults(fn=func, fn_schema=schema))
            else:
                tools.append(FunctionTool.from_defaults(fn=func))
        except (ImportError, AttributeError):
            logger.warning(f"Could not load entertainment tool: {mod}.{fn}")
    return tools


def _get_system_tools() -> list[FunctionTool]:
    """Get on-demand system tools."""
    from aria.tools.schemas import HttpRequestSchema, ProcessSchema

    tool_specs = [
        ("aria.tools.http", "http_request"),
        ("aria.tools.process", "process"),
    ]
    explicit_schemas = {
        "http_request": HttpRequestSchema,
        "process": ProcessSchema,
    }
    tools: list[FunctionTool] = []
    for mod, fn in tool_specs:
        func = _import_function(mod, fn)
        schema = explicit_schemas.get(fn)
        if schema is not None:
            tools.append(FunctionTool.from_defaults(fn=func, fn_schema=schema))
        else:
            tools.append(FunctionTool.from_defaults(fn=func))
    return tools


def _get_ax_tools() -> list[FunctionTool]:
    """Single unified ax dispatcher tool."""
    from aria.tools.ax import ax
    from aria.tools.ax.dispatcher import AxSchema

    return [FunctionTool.from_defaults(async_fn=ax, fn_schema=AxSchema)]


_CATEGORY_LOADERS: dict[str, Callable[[], list[FunctionTool]]] = {
    CORE_LITE: _get_core_lite_tools,
    FILES_LITE: _get_file_lite_tools,
    CORE: _get_core_tools,
    FILES: _get_file_tools,
    AX: _get_ax_tools,
    WEB: _get_web_tools,
    DEVELOPMENT: _get_development_tools,
    FINANCE: _get_finance_tools,
    ENTERTAINMENT: _get_entertainment_tools,
    SYSTEM: _get_system_tools,
}


def get_tools(categories: list[str] | None = None) -> list[FunctionTool]:
    """Get tools by category. None returns all tools.

    When multiple categories are loaded, tools are deduplicated by name
    so the same tool is never registered twice.

    Args:
        categories: List of category names to load.
            None loads all categories.

    Returns:
        List of FunctionTool instances (deduplicated by name).
    """
    if categories is None:
        categories = ALL_CATEGORIES

    tools: list[FunctionTool] = []
    seen: set[str] = set()
    for cat in categories:
        loader = _CATEGORY_LOADERS.get(cat)
        if loader is None:
            logger.warning(f"Unknown tool category: {cat}")
            continue
        try:
            for tool in loader():
                name = tool.metadata.name or ""
                if name not in seen:
                    tools.append(tool)
                    seen.add(name)
        except Exception as exc:
            logger.error(f"Failed to load {cat} tools: {exc}")

    return tools
