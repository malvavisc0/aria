import json

import yfinance as yf
from agno.tools.toolkit import Toolkit


class YFinanceTools(Toolkit):
    def __init__(self):
        super().__init__(name="yfinance_tools")
        self.register(self.get_current_price)
        self.register(self.get_company_information)
        self.register(self.get_news)
        self.register(self.get_income_statement)
        self.register(self.get_quarterly_financials)
        self.register(self.get_balance_sheet)
        self.register(self.get_quarterly_balance_sheet)
        self.register(self.get_cashflow)
        self.register(self.get_quarterly_cashflow)
        self.register(self.get_major_holders)
        self.register(self.get_institutional_holders)
        self.register(self.get_recommendations)
        self.register(self.get_sustainability_scores)
        self.register(self.get_price_history)

    def get_current_price(self, ticker: str) -> str:
        """
        Retrieves the current price of a stock given its ticker symbol.

        Args:
         ticker (str): The ticker symbol of the stock.

        Returns:
         str: The current price of the stock formatted to four decimal places.

        Raises:
            ValueError: If the current price for the given ticker cannot be found.
        """
        current_price = yf.Ticker(ticker).info.get("regularMarketPrice")
        if not current_price:
            raise ValueError(f"Could not find current price for {ticker}")
        return f"{current_price:.2f}"

    def get_company_information(self, ticker: str) -> str:
        """
        Retrieve information about a company using its ticker symbol.

        Args:
         ticker (str): The ticker symbol of the company.

        Returns:
         str: A dictionary containing various pieces of information about the company.
        """
        company_info_full = yf.Ticker(ticker).info
        company_info_cleaned = {
            "Name": company_info_full.get("shortName"),
            "Symbol": company_info_full.get("symbol"),
            "Current Stock Price": f"{company_info_full.get('regularMarketPrice', company_info_full.get('currentPrice'))} {company_info_full.get('currency', 'USD')}",
            "Market Cap": f"{company_info_full.get('marketCap', company_info_full.get('enterpriseValue'))} {company_info_full.get('currency', 'USD')}",
            "Sector": company_info_full.get("sector"),
            "Industry": company_info_full.get("industry"),
            "Address": company_info_full.get("address1"),
            "City": company_info_full.get("city"),
            "State": company_info_full.get("state"),
            "Zip": company_info_full.get("zip"),
            "Country": company_info_full.get("country"),
            "EPS": company_info_full.get("trailingEps"),
            "P/E Ratio": company_info_full.get("trailingPE"),
            "52 Week Low": company_info_full.get("fiftyTwoWeekLow"),
            "52 Week High": company_info_full.get("fiftyTwoWeekHigh"),
            "50 Day Average": company_info_full.get("fiftyDayAverage"),
            "200 Day Average": company_info_full.get("twoHundredDayAverage"),
            "Website": company_info_full.get("website"),
            "Summary": company_info_full.get("longBusinessSummary"),
            "Analyst Recommendation": company_info_full.get("recommendationKey"),
            "Number Of Analyst Opinions": company_info_full.get(
                "numberOfAnalystOpinions"
            ),
            "Employees": company_info_full.get("fullTimeEmployees"),
            "Total Cash": company_info_full.get("totalCash"),
            "Free Cash flow": company_info_full.get("freeCashflow"),
            "Operating Cash flow": company_info_full.get("operatingCashflow"),
            "EBITDA": company_info_full.get("ebitda"),
            "Revenue Growth": company_info_full.get("revenueGrowth"),
            "Gross Margins": company_info_full.get("grossMargins"),
            "Ebitda Margins": company_info_full.get("ebitdaMargins"),
        }
        json_doc = json.dumps(company_info_cleaned, indent=0)
        return json_doc.replace("\n", "").replace("\r\n", "").replace("\r", "")

    def get_news(self, ticker: str) -> str:
        """
        Retrieve the latest news articles for a given stock ticker.

        Args:
         ticker (str): The stock ticker symbol for which to retrieve news.

        Returns:
         str: A list of news articles related to the stock ticker.

        Raises:
         Exception: If an error occurs while retrieving the news.
        """
        news = []
        results = yf.Ticker(ticker).news
        for row in results:
            article = {
                "Title": row["content"]["title"],
                "Summary": row["content"]["summary"],
                "Date": row["content"]["pubDate"],
                "Link": row["content"]["canonicalUrl"]["url"],
            }
            news.append(article)
        json_doc = json.dumps(news, indent=0)
        return json_doc.replace("\n", "").replace("\r\n", "").replace("\r", "")

    def get_earnings_history(self, ticker: str) -> str:
        """
        Retrieves the earnings history for a specified stock ticker.

        Args:
         ticker (str): The stock ticker symbol for which to retrieve the earnings history.

        Returns:
         str: A JSON string representation of the earnings history.
        """
        return self._obj_to_json_string(yf.Ticker(ticker).earnings_history)

    def get_income_statement(self, ticker: str) -> str:
        """
        Retrieves the income statement for a given stock ticker in JSON format.

        Args:
         ticker (str): The stock ticker symbol for which to retrieve the income statement.

        Returns:
         str: The income statement data in JSON format.
        """
        return self._obj_to_json_string(yf.Ticker(ticker).financials)

    def get_quarterly_financials(self, ticker: str) -> str:
        """
        Retrieve the quarterly financials for a given stock ticker.

        Args:
         ticker (str): The stock ticker symbol for which to retrieve the quarterly financials.

        Returns:
         str: A JSON string representation of the quarterly financials.
        """
        return self._obj_to_json_string(yf.Ticker(ticker).quarterly_financials)

    def get_balance_sheet(self, ticker: str) -> str:
        """
        Retrieve the balance sheet for a given stock ticker.

        Args:
         ticker (str): The stock ticker symbol for which to retrieve the balance sheet.

        Returns:
         str: A JSON string representing the balance sheet data for the specified ticker.
        """
        return self._obj_to_json_string(yf.Ticker(ticker).balance_sheet)

    def get_quarterly_balance_sheet(self, ticker: str) -> str:
        """
        Retrieve the quarterly balance sheet for a given stock ticker.

        Args:
         ticker (str): The stock ticker symbol for which to retrieve the balance sheet.

        Returns:
         str: The quarterly balance sheet in JSON format.
        """
        return self._obj_to_json_string(yf.Ticker(ticker).quarterly_balance_sheet)

    def get_cashflow(self, ticker: str) -> str:
        """
        Retrieve the annual cash flow statement for a given stock ticker.

        Args:
         ticker (str): The stock ticker symbol for which to retrieve the cash flow statement.

        Returns:
         str: The annual cash flow statement in JSON format.
        """
        return self._obj_to_json_string(yf.Ticker(ticker).cashflow)

    def get_quarterly_cashflow(self, ticker: str) -> str:
        """
        Retrieve the quarterly cash flow statement for a given stock ticker.

        Args:
         ticker (str): The stock ticker symbol for which to retrieve the cash flow statement.

        Returns:
         str: The quarterly cash flow statement in JSON format.
        """
        return self._obj_to_json_string(yf.Ticker(ticker).quarterly_cashflow)

    def get_major_holders(self, ticker: str) -> str:
        """
        Retrieve the list of major shareholders for a given stock ticker.

        Args:
         ticker (str): The stock ticker symbol for which to retrieve the major shareholders.

        Returns:
         str: The list of major shareholders in JSON format.
        """
        return self._obj_to_json_string(yf.Ticker(ticker).major_holders)

    def get_institutional_holders(self, ticker: str) -> str:
        """
        Retrieve the list of institutional shareholders for a given stock ticker.

        Args:
         ticker (str): The stock ticker symbol for which to retrieve the institutional shareholders.

        Returns:
         str: The list of institutional shareholders in JSON format.
        """
        return self._obj_to_json_string(yf.Ticker(ticker).institutional_holders)

    def get_recommendations(self, ticker: str) -> str:
        """
        Retrieve stock recommendations for a given ticker.

        Args:
         ticker (str): The stock ticker symbol for which to retrieve recommendations.

        Returns:
         str: A JSON string containing the stock recommendations.
        """
        return self._obj_to_json_string(yf.Ticker(ticker).recommendations)

    def get_sustainability_scores(self, ticker: str) -> str:
        """
        Retrieve sustainability scores for a given stock ticker.

        This method uses the Yahoo Finance API to fetch sustainability data for the specified stock ticker.
        It extracts the ESG (Environmental, Social, and Governance) scores, as well as environment, social,
        and governance scores, and returns them in a JSON formatted string.

        Args:
         ticker (str): The stock ticker symbol for which to retrieve the sustainability scores.

        Returns:
         str: A JSON string containing the sustainability scores.
        """
        sustainability = yf.Ticker(ticker).sustainability.to_json()
        json_object = json.loads(sustainability)
        json_doc = {
            "ESG": json_object["esgScores"]["totalEsg"],
            "Environment": json_object["esgScores"]["environmentScore"],
            "Social": json_object["esgScores"]["socialScore"],
            "Governance": json_object["esgScores"]["governanceScore"],
        }
        json_doc = json.dumps(json_doc, indent=0)
        return json_doc.replace("\n", "").replace("\r\n", "").replace("\r", "")

    def get_price_history(
        self, ticker: str, period: str = "10y", interval: str = "1d"
    ) -> str:
        """
        Retrieves the price history of a specified stock ticker.

        Args:
         ticker (str): The stock ticker symbol for which to retrieve the price history.
         period (str, optional): The time period for which to retrieve the price history. Defaults to "10y".
         interval (str, optional): The time interval at which to retrieve the price history. Defaults to "1d".

        Returns:
         str: The price history data in JSON format.
        """
        return self._obj_to_json_string(
            yf.Ticker(ticker).history(period=period, interval=interval)
        )

    def _obj_to_json_string(self, obj: object) -> str:
        json_doc = obj.to_json()
        return json_doc.replace("\n", "").replace("\r\n", "").replace("\r", "")
