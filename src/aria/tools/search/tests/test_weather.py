import json

import httpx

from aria.tools.search.weather import get_current_weather


def test_get_current_weather_success(monkeypatch):
    def fake_get(url, params=None, timeout=None):
        request = httpx.Request("GET", url)
        if "geocoding-api.open-meteo.com" in url:
            return httpx.Response(
                200,
                request=request,
                json={
                    "results": [
                        {
                            "name": "Berlin",
                            "country": "Germany",
                            "latitude": 52.52,
                            "longitude": 13.405,
                            "timezone": "Europe/Berlin",
                        }
                    ]
                },
            )
        if "api.open-meteo.com" in url:
            return httpx.Response(
                200,
                request=request,
                json={
                    "current": {
                        "time": "2026-01-29T19:00",
                        "temperature_2m": 3.2,
                        "wind_speed_10m": 12.3,
                        "weather_code": 3,
                    }
                },
            )
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(httpx, "get", fake_get)

    out = json.loads(get_current_weather("need current conditions", "Berlin"))
    assert out["status"] == "success"
    assert out["data"]["resolved"]["name"] == "Berlin"
    assert out["data"]["current"]["conditions"]


def test_get_current_weather_no_geocode_results(monkeypatch):
    def fake_get(url, params=None, timeout=None):
        if "geocoding-api.open-meteo.com" in url:
            return httpx.Response(
                200,
                request=httpx.Request("GET", url),
                json={"results": []},
            )
        raise AssertionError("Forecast should not be requested")

    monkeypatch.setattr(httpx, "get", fake_get)

    out = json.loads(get_current_weather("test", "Nowhere"))
    assert out["status"] == "error"
    assert "No geocoding result" in out["error"]["message"]


def test_get_current_weather_requires_location():
    out = json.loads(get_current_weather("test", ""))
    assert out["status"] == "error"
    assert "location" in out["error"]["message"]
