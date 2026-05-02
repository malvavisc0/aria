"""Finance CLI commands.

Wraps Yahoo Finance tools as CLI sub-commands that output JSON.
"""

import typer

app = typer.Typer(
    help="Stock prices, company fundamentals, and ticker news via Yahoo Finance.",
)


@app.command("stock")
def stock_cmd(
    ticker: str = typer.Argument(..., help="Stock symbol (e.g. AAPL, BTC-USD)"),
):
    """Fetch current stock/crypto price."""
    from aria.tools.search import fetch_current_stock_price

    result = fetch_current_stock_price(reason="CLI stock price lookup", ticker=ticker)
    typer.echo(result)


@app.command("company")
def company_cmd(
    ticker: str = typer.Argument(..., help="Stock symbol (e.g. AAPL)"),
):
    """Fetch company fundamentals and metadata."""
    from aria.tools.search import fetch_company_information

    result = fetch_company_information(reason="CLI company info lookup", ticker=ticker)
    typer.echo(result)


@app.command("news")
def news_cmd(
    ticker: str = typer.Argument(..., help="Stock symbol (e.g. AAPL)"),
    max_articles: int = typer.Option(
        10, "--max-articles", "-n", help="Number of articles (1-50)"
    ),
):
    """Fetch recent news for a stock ticker."""
    from aria.tools.search import fetch_ticker_news

    result = fetch_ticker_news(
        reason="CLI ticker news lookup",
        ticker=ticker,
        max_articles=max_articles,
    )
    typer.echo(result)
