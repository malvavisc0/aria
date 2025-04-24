import json
import os
import tempfile
import urllib.parse
from typing import Optional

import httpx
from agno.tools.toolkit import Toolkit
from agno.utils.log import log_info
from markitdown import MarkItDown

BYPARR_URL = os.environ.get("BYPARR_URL", "http://byparr:8191/v1")
BYPARR_TIMEOUT = os.environ.get("BYPARR_TIMEOUT", 30)


class SearxngTools(Toolkit):
    def __init__(
        self,
        host: str,
        max_results: Optional[int] = 10,
    ):
        super().__init__(name="searxng")

        self.host = host
        self.max_results = max_results

        self.register(self.search_the_web)
        self.register(self.search_only_news)

    def search_the_web(self, query: str, max_results: int = 10) -> str:
        """Use this function to search the web.

        Args:
            query (str): The query to search the web with.
            max_results (int, optional): The maximum number of results to return. Defaults to 10.

        Returns:
            The results of the search.
        """
        return self._search(query, max_results=max_results)

    def search_only_news(self, query: str, max_results: int = 10) -> str:
        """Use this function to search for news.

        Args:
            query (str): The query to search news with.
            max_results (int, optional): The maximum number of results to return. Defaults to 10.

        Returns:
            The results of the search.
        """
        return self._search(query, "news", max_results)

    def _search(
        self, query: str, category: Optional[str] = None, max_results: int = 10
    ) -> str:
        encoded_query = urllib.parse.quote(query)
        url = f"{self.host}/search?format=json&q={encoded_query}"

        if category:
            url += f"&categories={category}"

        count = self.max_results or max_results

        log_info(f"Fetching results from searxng: {url}")
        try:
            response = httpx.get(url).json()["results"][:count]
            results = [
                {
                    "title": row["title"],
                    "url": row["url"],
                    "summary": row["content"],
                    # "content": self._get_content(row["url"]),
                }
                for row in response
            ]
            return json.dumps(results)
        except Exception as e:
            return f"Error fetching results from searxng: {e}"

    def _get_content(self, url: str) -> str:
        try:
            solution = httpx.post(
                url=BYPARR_URL,
                headers={"Content-Type": "application/json"},
                json={
                    "cmd": "request.get",
                    "url": url,
                    "maxTimeout": BYPARR_TIMEOUT,
                },
                timeout=float(BYPARR_TIMEOUT),
            ).json()
            if "solution" not in solution:
                return ""
            raw_html = solution["solution"]["response"]
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_file_path = os.path.join(temp_dir, "raw.html")
                with open(temp_file_path, "w") as temp_file:
                    temp_file.write(raw_html)
                    return MarkItDown().convert(temp_file.name).markdown
        except Exception as e:
            log_info(f"Error while parsing {url}: {e}")
            return ""
