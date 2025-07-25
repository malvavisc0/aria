from os import environ

from enhancedtoolkits import (
    DownloaderTools,
    ReasoningTools,
    SearxngTools,
    ThinkingTools,
    WeatherTools,
    YFinanceTools,
    YouTubeTools,
)
from enhancedtoolkits.calculators import ArithmeticCalculatorTools

searxng_tools = SearxngTools(
    host=environ.get("SEARXNG_URL", ""),
    enable_content_fetching=True,
    byparr_enabled=True,
    max_results=5,
)
downloader_tools = DownloaderTools(
    byparr_enabled=True,
    max_retries=3,
    timeout=60,
    user_agent_rotation=True,
    enable_caching=False,
)
calculator_tools = ArithmeticCalculatorTools()
reasoning_tools = ReasoningTools()
yfinance_tools = YFinanceTools()
youtube_tools = YouTubeTools()
weather_tools = WeatherTools()
thinking_tools = ThinkingTools()
