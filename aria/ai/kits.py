from os import environ

from enhancedtoolkits import (
    CalculatorTools,
    ReasoningTools,
    SearxngTools,
    YFinanceTools,
    YouTubeTools,
)

calulator_tools = CalculatorTools()

reasoning_tools = ReasoningTools()

searxng_tools = SearxngTools(
    host=environ.get("SEARXNG_URL", ""), enable_content_fetching=True, byparr_enabled=True
)

yfinance_tools = YFinanceTools()

youtube_tools = YouTubeTools()
