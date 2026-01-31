# Web Search Tools (`aria.tools.search.duckduckgo`)

This file documents the tools implemented in [`aria.tools.search.duckduckgo`](src/aria2/tools/search/duckduckgo.py:1).

### `web_search(intent: str, query: str, max_results: int = 5)`

Search the web and return a small set of results.

When to use: Research current information not available in local files.

Parameters:
- `intent`: Your intended outcome with this tool call.
- `query`: Search query string.
- `max_results`: Number of results to return (default: 5).

Returns:
- JSON string with an `operation` field and a `result` list of `{title, href}`.

Example:
```python
web_search("Find official documentation for httpx timeouts", "httpx timeout docs", max_results=5)
```

