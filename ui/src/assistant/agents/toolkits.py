from agno.tools.arxiv import ArxivTools
from agno.tools.pubmed import PubmedTools
from agno.tools.reasoning import ReasoningTools
from agno.tools.website import WebsiteTools
from agno.tools.wikipedia import WikipediaTools
from assistant.agents.tools.finance import YFinanceTools
from assistant.agents.tools.searxng import SearxngTools
from assistant.agents.tools.youtube import YouTubeTools

arxiv = ArxivTools()
finance = YFinanceTools()
wikipedia = WikipediaTools()
website = WebsiteTools()
youtube = YouTubeTools()
searxng = SearxngTools(host="http://searxng:8080", max_results=50)
pubmed = PubmedTools()
website = WebsiteTools()
wikipedia = WikipediaTools()
reasoning = ReasoningTools()
