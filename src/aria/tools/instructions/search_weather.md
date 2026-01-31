# Weather Tools (`aria.tools.search.weather`)

This file documents the tools implemented in [`aria.tools.search.weather`](src/aria2/tools/search/weather.py:1).

### `get_current_weather(intent: str, location: str)`

Fetch current weather conditions using Open-Meteo (no API key).

When to use: User asks for current weather for a city/place.

Parameters:
- `intent`: Your intended outcome with this tool call.
- `location`: Free-form city/place string (for example `Berlin`, `San Francisco`).

Returns:
- JSON string with resolved geocoding and current conditions, or an error.

