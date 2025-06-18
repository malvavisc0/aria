from os import environ

from enhancedtoolkits import (
    CalculatorTools,
    ReasoningTools,
    SearxngTools,
    WeatherTools,
    YFinanceTools,
    YouTubeTools,
)

searxng_tools = SearxngTools(
    host=environ.get("SEARXNG_URL", ""), enable_content_fetching=True, byparr_enabled=True
)
calulator_tools = CalculatorTools()
reasoning_tools = ReasoningTools()
yfinance_tools = YFinanceTools()
youtube_tools = YouTubeTools()
weather_tools = WeatherTools()
