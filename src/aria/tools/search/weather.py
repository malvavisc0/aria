"""Open-Meteo-backed weather tool (no API key)."""

from __future__ import annotations

from typing import Any, Dict, Optional

import httpx
from loguru import logger

from aria.tools import (
    get_function_name,
    log_tool_call,
    tool_error_response,
    tool_success_response,
)
from aria.tools.constants import NETWORK_TIMEOUT

# https://open-meteo.com/en/docs
_WEATHER_CODE_TEXT: dict[int, str] = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Drizzle: light",
    53: "Drizzle: moderate",
    55: "Drizzle: dense",
    56: "Freezing drizzle: light",
    57: "Freezing drizzle: dense",
    61: "Rain: slight",
    63: "Rain: moderate",
    65: "Rain: heavy",
    66: "Freezing rain: light",
    67: "Freezing rain: heavy",
    71: "Snow fall: slight",
    73: "Snow fall: moderate",
    75: "Snow fall: heavy",
    77: "Snow grains",
    80: "Rain showers: slight",
    81: "Rain showers: moderate",
    82: "Rain showers: violent",
    85: "Snow showers: slight",
    86: "Snow showers: heavy",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


def _ok(intent: str, result: Dict[str, Any]) -> str:
    return tool_success_response(get_function_name(), intent, result)


def _err(intent: str, message: str) -> str:
    return tool_error_response(
        get_function_name(), intent, RuntimeError(message)
    )


def _get_weather_text(code: Optional[int]) -> str:
    if code is None:
        return "Unknown"
    return _WEATHER_CODE_TEXT.get(code, f"Unknown (code={code})")


@log_tool_call
def get_current_weather(intent: str, location: str) -> str:
    """Get current weather for a city/location string using Open-Meteo.

    Args:
        intent: Why you're checking (e.g., "Planning outdoor activity")
        location: City name (e.g., "Berlin") or free-form place name

    Returns:
        JSON with temperature, wind_speed, weather_code, weather_text.
        No API key required.
    """

    location_value = (location or "").strip()
    if not location_value:
        return _err(intent, "location must be a non-empty string")

    # Logging handled by @log_tool_call decorator

    try:
        # 1) Geocode
        geo = httpx.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": location_value, "count": 1, "format": "json"},
            timeout=httpx.Timeout(NETWORK_TIMEOUT),
        )
        geo.raise_for_status()
        geo_json = geo.json()
        results = geo_json.get("results") or []
        if not results:
            return _err(
                intent, f"No geocoding result for location: {location_value}"
            )

        first = results[0]
        lat = first.get("latitude")
        lon = first.get("longitude")
        if lat is None or lon is None:
            return _err(
                intent, "Geocoding response missing latitude/longitude"
            )

        resolved_name = first.get("name") or location_value
        country = first.get("country")
        timezone = first.get("timezone")

        # 2) Forecast (current)
        forecast = httpx.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "current": [
                    "temperature_2m",
                    "wind_speed_10m",
                    "weather_code",
                ],
                "timezone": "auto",
            },
            timeout=httpx.Timeout(NETWORK_TIMEOUT),
        )
        forecast.raise_for_status()
        fjson = forecast.json()
        current = fjson.get("current") or {}

        weather_code = current.get("weather_code")

        return _ok(
            intent,
            {
                "tool": "get_current_weather",
                "query": {"location": location_value},
                "resolved": {
                    "name": resolved_name,
                    "country": country,
                    "latitude": lat,
                    "longitude": lon,
                    "timezone": timezone,
                },
                "current": {
                    "time": current.get("time"),
                    "temperature_c": current.get("temperature_2m"),
                    "wind_speed_kmh": current.get("wind_speed_10m"),
                    "weather_code": weather_code,
                    "conditions": _get_weather_text(weather_code),
                },
            },
        )
    except httpx.HTTPError as exc:
        logger.warning(f"Weather lookup failed for {location_value}: {exc}")
        return _err(intent, f"Weather request failed: {exc}")
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.exception("Unexpected error in get_current_weather")
        return _err(intent, f"Unexpected error: {type(exc).__name__}: {exc}")


__all__ = ["get_current_weather"]
