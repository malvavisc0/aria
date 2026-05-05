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

from typing import Callable, Dict, List, Optional

from llama_index.core.tools import FunctionTool
from loguru import logger

# Tool categories
CORE_LITE = "core_lite"
FILES_LITE = "files_lite"
CORE = "core"
FILES = "files"
WEB = "web"
DEVELOPMENT = "development"
FINANCE = "finance"
ENTERTAINMENT = "entertainment"
SYSTEM = "system"

ALL_CATEGORIES = [
    CORE,
    FILES,
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


def _get_core_lite_tools() -> List[FunctionTool]:
    """Aria agent core tools: reasoning + shell only."""
    from aria.tools.shell.functions import ShellToolSchema

    tool_specs = [
        ("aria.tools.reasoning", "reasoning"),
        ("aria.tools.shell", "shell"),
    ]
    tools = []
    for mod, fn in tool_specs:
        func = _import_function(mod, fn)
        if fn == "shell":
            tools.append(FunctionTool.from_defaults(fn=func, fn_schema=ShellToolSchema))
        else:
            tools.append(FunctionTool.from_defaults(fn=func))
    return tools


def _get_file_lite_tools() -> List[FunctionTool]:
    """Aria agent file tools: no file_info or copy_file."""
    tool_specs = [
        ("aria.tools.files", "read_file"),
        ("aria.tools.files", "write_file"),
        ("aria.tools.files", "edit_file"),
        ("aria.tools.files", "list_files"),
        ("aria.tools.files", "search_files"),
    ]
    return [
        FunctionTool.from_defaults(fn=_import_function(mod, fn))
        for mod, fn in tool_specs
    ]


def _get_core_tools() -> List[FunctionTool]:
    """Worker core tools: reasoning, plan, scratchpad, shell."""
    from aria.tools.shell.functions import ShellToolSchema

    tool_specs = [
        ("aria.tools.reasoning", "reasoning"),
        ("aria.tools.planner", "plan"),
        ("aria.tools.scratchpad", "scratchpad"),
        ("aria.tools.shell", "shell"),
    ]
    tools = []
    for mod, fn in tool_specs:
        func = _import_function(mod, fn)
        if fn == "shell":
            tools.append(FunctionTool.from_defaults(fn=func, fn_schema=ShellToolSchema))
        else:
            tools.append(FunctionTool.from_defaults(fn=func))
    return tools


def _get_file_tools() -> List[FunctionTool]:
    """Worker file tools: full set including file_info and copy_file."""
    tool_specs = [
        ("aria.tools.files", "read_file"),
        ("aria.tools.files", "write_file"),
        ("aria.tools.files", "edit_file"),
        ("aria.tools.files", "file_info"),
        ("aria.tools.files", "list_files"),
        ("aria.tools.files", "search_files"),
        ("aria.tools.files", "copy_file"),
    ]
    return [
        FunctionTool.from_defaults(fn=_import_function(mod, fn))
        for mod, fn in tool_specs
    ]


def _get_web_tools() -> List[FunctionTool]:
    """Get on-demand browser tools."""
    try:
        from aria.config.api import Lightpanda

        if not Lightpanda.is_available():
            logger.debug("Browser tools not available (Lightpanda)")
            return []
    except Exception:
        return []

    tool_specs = [
        ("aria.tools.browser", "open_url"),
        ("aria.tools.browser", "browser_click"),
    ]
    tools = []
    for mod, fn in tool_specs:
        try:
            tools.append(FunctionTool.from_defaults(async_fn=_import_function(mod, fn)))
        except (ImportError, AttributeError):
            logger.warning(f"Could not load browser tool: {mod}.{fn}")
    return tools


def _get_development_tools() -> List[FunctionTool]:
    """Get on-demand development tools."""
    tool_specs = [
        ("aria.tools.development", "python"),
    ]
    return [
        FunctionTool.from_defaults(fn=_import_function(mod, fn))
        for mod, fn in tool_specs
    ]


def _get_finance_tools() -> List[FunctionTool]:
    """Get on-demand finance tools."""
    tool_specs = [
        ("aria.tools.search", "fetch_current_stock_price"),
        ("aria.tools.search", "fetch_company_information"),
        ("aria.tools.search", "fetch_ticker_news"),
    ]
    return [
        FunctionTool.from_defaults(fn=_import_function(mod, fn))
        for mod, fn in tool_specs
    ]


def _get_entertainment_tools() -> List[FunctionTool]:
    """Get on-demand entertainment tools."""
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
    tools = []
    for mod, fn in tool_specs:
        try:
            tools.append(FunctionTool.from_defaults(fn=_import_function(mod, fn)))
        except (ImportError, AttributeError):
            logger.warning(f"Could not load entertainment tool: {mod}.{fn}")
    return tools


def _get_system_tools() -> List[FunctionTool]:
    """Get on-demand system tools."""
    tool_specs = [
        ("aria.tools.http", "http_request"),
        ("aria.tools.process", "process"),
    ]
    return [
        FunctionTool.from_defaults(fn=_import_function(mod, fn))
        for mod, fn in tool_specs
    ]


_CATEGORY_LOADERS: Dict[str, Callable[[], List[FunctionTool]]] = {
    CORE_LITE: _get_core_lite_tools,
    FILES_LITE: _get_file_lite_tools,
    CORE: _get_core_tools,
    FILES: _get_file_tools,
    WEB: _get_web_tools,
    DEVELOPMENT: _get_development_tools,
    FINANCE: _get_finance_tools,
    ENTERTAINMENT: _get_entertainment_tools,
    SYSTEM: _get_system_tools,
}


def get_tools(categories: Optional[List[str]] = None) -> List[FunctionTool]:
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

    tools: List[FunctionTool] = []
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


def get_core_tools() -> List[FunctionTool]:
    """Get always-loaded core tools (reasoning, plan, knowledge, etc.)."""
    return get_tools([CORE])


def get_file_tools() -> List[FunctionTool]:
    """Get always-loaded file tools."""
    return get_tools([FILES])


def get_domain_tools(domain: str) -> List[FunctionTool]:
    """Get on-demand domain tools.

    Args:
        domain: One of: web, development, finance, entertainment, system.

    Returns:
        List of FunctionTool instances for the domain.
    """
    return get_tools([domain])
