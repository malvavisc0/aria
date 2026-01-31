# Finance Tools (`aria.tools.search.finance`)

This file documents the tools implemented in [`aria.tools.search.finance`](src/aria2/tools/search/finance.py:1).

### `fetch_current_stock_price(intent: str, ticker: str)`

Fetch current price for a ticker.

Parameters:
- `intent`: Your intended outcome with this tool call.
- `ticker`: Stock/crypto ticker symbol (for example `AAPL`, `MSFT`, `BTC-USD`).

Returns:
- JSON string with current price and basic context, or an error payload.

### `fetch_company_information(intent: str, ticker: str)`

Fetch company fundamentals/metadata for a ticker.

### `fetch_ticker_news(intent: str, ticker: str, max_articles: int = 10)`

Fetch recent news for a ticker.

Parameters:
- `intent`: Your intended outcome with this tool call.
- `ticker`: Stock/crypto ticker symbol.
- `max_articles`: Number of articles to return (1..50).

