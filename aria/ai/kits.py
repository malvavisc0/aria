from os import environ

from enhancedtoolkits import (
    CalculatorTools,
    DownloaderTools,
    ReasoningTools,
    SearxngTools,
    WeatherTools,
    YFinanceTools,
    YouTubeTools,
)

searxng_tools = SearxngTools(
    host=environ.get("SEARXNG_URL", ""),
    enable_content_fetching=True,
    byparr_enabled=True,
    max_results=5,
)
downloader_tools = DownloaderTools(
    byparr_enabled=True,
    max_retries=3,
    timeout=30,
    user_agent_rotation=True,
    enable_caching=False,
)
calulator_tools = CalculatorTools()
reasoning_tools = ReasoningTools()
yfinance_tools = YFinanceTools()
youtube_tools = YouTubeTools()
weather_tools = WeatherTools()
