"""Yahoo Finance-backed market data tools."""

import inspect
import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import yfinance
from loguru import logger


class YFinanceError(Exception):
    """Custom exception for YFinance-related errors."""


class YFinanceValidationError(YFinanceError):
    """Exception for input validation errors."""


class YFinanceDataError(YFinanceError):
    """Exception for data retrieval errors."""


# Valid ticker symbol pattern (letters, numbers, dots, hyphens)
TICKER_PATTERN = re.compile(r"^[A-Z0-9.-]{1,10}$")

# Common quote currencies for crypto pairs where users often omit the dash.
# Examples:
# - BTCUSD -> BTC-USD
# - ETH/EUR -> ETH-EUR
_CRYPTO_QUOTE_CURRENCIES = {
    "USD",
    "EUR",
    "GBP",
    "JPY",
    "CHF",
    "AUD",
    "CAD",
}

# News article limits
MIN_ARTICLES = 1
MAX_ARTICLES = 50


def fetch_current_stock_price(intent: str, ticker: str) -> str:
    """
    Fetch current price for a ticker.

    Args:
        intent: Why you're fetching (e.g., "Checking portfolio value")
        ticker: Stock symbol (e.g., AAPL, GOOGL, BTC-USD)

    Returns:
        JSON with current_price, currency, market_state, day_change,
        day_change_percent, previous_close.
    """
    logger.info(f"fetch_current_stock_price called with ticker='{ticker}'")
    raw_ticker = ticker
    try:
        ticker = _validate_ticker(ticker)
        logger.debug(f"Ticker validated: {ticker}")
        frame = inspect.currentframe()
        if frame:
            func_name = frame.f_code.co_name
            logger.debug(f"Calling {func_name} to achieve: {intent}")

        ticker_obj = _get_ticker(ticker)
        logger.debug(f"Ticker object created for {ticker}")

        info = _get_ticker_info(ticker_obj, ticker)
        logger.debug(f"Ticker info retrieved, keys: {list(info.keys())[:10]}")

        # Try multiple price fields
        current_price = (
            info.get("regularMarketPrice")
            or info.get("currentPrice")
            or info.get("previousClose")
        )

        if current_price is None:
            raise YFinanceDataError(f"No price data available for {ticker}")

        # Get additional price context
        currency = info.get("currency", "USD")
        market_state = info.get("marketState", "UNKNOWN")

        result = {
            "ticker": ticker,
            "current_price": round(float(current_price), 2),
            "currency": currency,
            "market_state": market_state,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "previous_close": info.get("previousClose"),
            "day_change": None,
            "day_change_percent": None,
        }

        # Calculate day change if possible
        prev_close = info.get("previousClose")
        if prev_close and current_price and prev_close != 0:
            day_change = current_price - prev_close
            day_change_percent = (day_change / prev_close) * 100
            result.update(
                {
                    "day_change": round(day_change, 2),
                    "day_change_percent": round(day_change_percent, 2),
                }
            )

        logger.info(
            f"Successfully fetched price for {ticker}: "
            f"${result['current_price']} {result['currency']}"
        )
        return _format_json_response(result)

    except YFinanceValidationError as exc:
        logger.error(f"Validation error for {raw_ticker}: {exc}")
        return _format_json_response(
            {
                "ticker": raw_ticker,
                "error": str(exc),
                "error_type": "validation_error",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
    except YFinanceDataError as exc:
        logger.error(f"Data error for {raw_ticker}: {exc}")
        hint = None
        if raw_ticker and isinstance(raw_ticker, str):
            normalized = _normalize_ticker(raw_ticker)
            if normalized != raw_ticker.strip().upper():
                hint = f"Try ticker '{normalized}'"
        return _format_json_response(
            {
                "ticker": raw_ticker,
                "error": str(exc),
                "error_type": "data_error",
                "hint": hint,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
    except Exception as exc:  # pylint: disable=broad-exception-caught
        # Important: tools should never raise here; an exception can crash the
        # agent.
        logger.exception(f"Unexpected error fetching price for {raw_ticker}: {exc}")
        return _format_json_response(
            {
                "ticker": raw_ticker,
                "error": f"Failed to get current price: {exc}",
                "error_type": "unexpected_error",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )


def fetch_company_information(intent: str, ticker: str) -> str:
    """
    Fetch company fundamentals/metadata for a ticker.

    Args:
        intent: Why you're fetching (e.g., "Researching investment")
        ticker: Stock symbol (e.g., AAPL, GOOGL)

    Returns:
        JSON with basic_info, financial_metrics, price_data,
        financial_health, analyst_data, location.
    """
    logger.info(f"fetch_company_information called with ticker='{ticker}'")
    raw_ticker = ticker
    try:
        ticker = _validate_ticker(ticker)
        logger.debug(f"Ticker validated: {ticker}")
        frame = inspect.currentframe()
        if frame:
            func_name = frame.f_code.co_name
            logger.debug(f"Calling {func_name} to achieve: {intent}")

        ticker_obj = _get_ticker(ticker)
        info = _get_ticker_info(ticker_obj, ticker)
        logger.debug(f"Retrieved company info for {ticker}")

        # Organize company information with safe extraction
        company_info = {
            "basic_info": {
                "name": info.get("shortName") or info.get("longName"),
                "symbol": info.get("symbol"),
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "website": info.get("website"),
                "summary": info.get("longBusinessSummary"),
                "employees": info.get("fullTimeEmployees"),
            },
            "financial_metrics": {
                "market_cap": info.get("marketCap"),
                "enterprise_value": info.get("enterpriseValue"),
                "trailing_pe": info.get("trailingPE"),
                "forward_pe": info.get("forwardPE"),
                "peg_ratio": info.get("pegRatio"),
                "price_to_book": info.get("priceToBook"),
                "eps_trailing": info.get("trailingEps"),
                "eps_forward": info.get("forwardEps"),
            },
            "price_data": {
                "current_price": info.get("regularMarketPrice")
                or info.get("currentPrice"),
                "currency": info.get("currency", "USD"),
                "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
                "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
                "fifty_day_average": info.get("fiftyDayAverage"),
                "two_hundred_day_average": info.get("twoHundredDayAverage"),
            },
            "financial_health": {
                "total_cash": info.get("totalCash"),
                "total_debt": info.get("totalDebt"),
                "free_cashflow": info.get("freeCashflow"),
                "operating_cashflow": info.get("operatingCashflow"),
                "ebitda": info.get("ebitda"),
                "revenue_growth": info.get("revenueGrowth"),
                "gross_margins": info.get("grossMargins"),
                "ebitda_margins": info.get("ebitdaMargins"),
            },
            "analyst_data": {
                "recommendation_key": info.get("recommendationKey"),
                "recommendation_mean": info.get("recommendationMean"),
                "number_of_analyst_opinions": info.get("numberOfAnalystOpinions"),
                "target_high_price": info.get("targetHighPrice"),
                "target_low_price": info.get("targetLowPrice"),
                "target_mean_price": info.get("targetMeanPrice"),
            },
            "location": {
                "address": info.get("address1"),
                "city": info.get("city"),
                "state": info.get("state"),
                "zip": info.get("zip"),
                "country": info.get("country"),
            },
            "metadata": {
                "ticker": ticker,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data_source": "Yahoo Finance",
            },
        }

        logger.info(
            f"Successfully fetched company info for {ticker}: "
            f"{company_info['basic_info'].get('name', 'Unknown')}"
        )
        return _format_json_response(company_info)

    except YFinanceValidationError as exc:
        logger.error(f"Validation error for {raw_ticker}: {exc}")
        return _format_json_response(
            {
                "ticker": raw_ticker,
                "error": str(exc),
                "error_type": "validation_error",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
    except YFinanceDataError as exc:
        logger.error(f"Data error for {raw_ticker}: {exc}")
        return _format_json_response(
            {
                "ticker": raw_ticker,
                "error": str(exc),
                "error_type": "data_error",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.exception(
            f"Unexpected error fetching company info for {raw_ticker}: {exc}"
        )
        return _format_json_response(
            {
                "ticker": raw_ticker,
                "error": f"Failed to get company information: {exc}",
                "error_type": "unexpected_error",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )


def fetch_ticker_news(intent: str, ticker: str, max_articles: int = 10) -> str:
    """
    Fetch recent news for a ticker.

    Args:
        intent: Why you're fetching (e.g., "Checking market sentiment")
        ticker: Stock symbol (e.g., AAPL, GOOGL)
        max_articles: Number of articles (default: 10, max: 50)

    Returns:
        JSON with articles[{title, publisher, link, publish_time}].
    """
    logger.info(
        f"fetch_ticker_news called with ticker='{ticker}', "
        f"max_articles={max_articles}"
    )
    raw_ticker = ticker
    try:
        ticker = _validate_ticker(ticker)
        logger.debug(f"Ticker validated: {ticker}")

        if not isinstance(max_articles, int):
            raise YFinanceValidationError("max_articles must be an integer")

        max_articles = max(MIN_ARTICLES, min(MAX_ARTICLES, max_articles))
        logger.debug(f"Max articles set to: {max_articles}")

        frame = inspect.currentframe()
        if frame:
            func_name = frame.f_code.co_name
            logger.debug(f"Calling {func_name} to achieve: {intent}")

        ticker_obj = _get_ticker(ticker)

        try:
            news_data = ticker_obj.news
        except Exception as exc:  # pylint: disable=broad-exception-caught
            raise YFinanceDataError(f"Failed to fetch news data: {exc}") from exc

        if not news_data:
            return _format_json_response(
                {
                    "ticker": ticker,
                    "articles": [],
                    "count": 0,
                    "message": "No news articles found",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )

        articles = []
        for article in news_data[:max_articles]:
            processed = _process_news_article(article)
            if processed:
                articles.append(processed)

        result = {
            "ticker": ticker,
            "articles": articles,
            "count": len(articles),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        logger.info(f"Successfully fetched {len(articles)} news articles for {ticker}")
        return _format_json_response(result)

    except YFinanceValidationError as exc:
        logger.error(f"Validation error for {raw_ticker} news: {exc}")
        return _format_json_response(
            {
                "ticker": raw_ticker,
                "articles": [],
                "count": 0,
                "error": str(exc),
                "error_type": "validation_error",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
    except YFinanceDataError as exc:
        logger.error(f"Data error for {raw_ticker} news: {exc}")
        return _format_json_response(
            {
                "ticker": raw_ticker,
                "articles": [],
                "count": 0,
                "error": str(exc),
                "error_type": "data_error",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.exception(f"Unexpected error fetching news for {raw_ticker}: {exc}")
        return _format_json_response(
            {
                "ticker": raw_ticker,
                "articles": [],
                "count": 0,
                "error": f"Failed to get news: {exc}",
                "error_type": "unexpected_error",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )


def _validate_ticker(ticker: Any) -> str:
    """
    Validate and normalize ticker symbol.

    Args:
        ticker (str): Raw ticker symbol

    Returns:
        Normalized ticker symbol
    """
    if ticker is None:
        raise YFinanceValidationError("Ticker symbol cannot be empty")
    if not isinstance(ticker, str):
        raise YFinanceValidationError("Ticker symbol must be a string")

    ticker = _normalize_ticker(ticker)

    if not ticker:
        raise YFinanceValidationError(
            "Ticker symbol cannot be empty after normalization"
        )

    if not TICKER_PATTERN.match(ticker):
        raise YFinanceValidationError(f"Invalid ticker symbol format: {ticker}")

    return ticker


def _normalize_ticker(ticker: str) -> str:
    """Normalize common user-entered ticker variants.

    This helps map user input to Yahoo Finance formats.
    """
    # Normalize ticker (uppercase, strip whitespace)
    normalized = str(ticker).strip().upper()

    # Support common pair delimiters for crypto/FX inputs.
    # BTC/USD -> BTC-USD
    if "/" in normalized:
        normalized = normalized.replace("/", "-")

    # Crypto pairs are commonly entered without a dash.
    # BTCUSD -> BTC-USD
    if "-" not in normalized:
        for quote in _CRYPTO_QUOTE_CURRENCIES:
            if normalized.endswith(quote) and len(normalized) > len(quote):
                base = normalized[: -len(quote)]
                if 2 <= len(base) <= 6:
                    normalized = f"{base}-{quote}"
                break

    return normalized


def _get_ticker(ticker: str) -> Any:
    """Get yfinance Ticker object."""
    return yfinance.Ticker(ticker)


def _get_ticker_info(ticker_obj: Any, ticker: str) -> Dict[str, Any]:
    """
    Get ticker info with error handling.

    Args:
        ticker_obj: YFinance Ticker object
        ticker: Ticker symbol for error messages

    Returns:
        Ticker info dictionary
    """
    try:
        info = ticker_obj.info
        if not info or not isinstance(info, dict):
            raise YFinanceDataError(f"No information available for {ticker}")
        return info
    except Exception as exc:
        raise YFinanceDataError(
            f"Failed to get ticker info for {ticker}: {exc}"
        ) from exc


def _format_json_response(data: Any) -> str:
    """
    Format response data as clean JSON string.

    Args:
        data: Data to format

    Returns:
        Clean JSON string
    """
    try:
        json_str = json.dumps(data, indent=2, ensure_ascii=False, default=str)
        return json_str
    except Exception as exc:
        return json.dumps({"error": f"Failed to format response: {exc}"})


def _process_news_article(article: Any) -> Optional[Dict[str, Any]]:
    """
    Process a single news article into standardized format.

    Args:
        article: Raw article data from yfinance

    Returns:
        Processed article dict or None if processing fails
    """
    try:
        if not isinstance(article, dict):
            return None

        if "content" in article:
            # New format
            content = article["content"]
            canonical_url = content.get("canonicalUrl", {})
            url = (
                canonical_url.get("url", "") if isinstance(canonical_url, dict) else ""
            )
            return {
                "title": content.get("title", "No title"),
                "summary": content.get("summary", ""),
                "published_date": content.get("pubDate", ""),
                "url": url,
                "source": article.get("source", "Unknown"),
            }
        else:
            # Direct format
            return {
                "title": article.get("title", "No title"),
                "summary": article.get("summary", ""),
                "published_date": article.get("providerPublishTime", ""),
                "url": article.get("link", ""),
                "source": article.get("publisher", "Unknown"),
            }
    except (KeyError, TypeError, ValueError):
        return None
