from agno.tools.arxiv import ArxivTools
from agno.tools.pubmed import PubmedTools
from agno.tools.calculator import CalculatorTools
from agno.tools.wikipedia import WikipediaTools

from assistant.agents.tools.finance import EnhancedYFinanceTools
from assistant.agents.tools.searxng import EnhancedSearxngTools
from assistant.agents.tools.youtube import EnhancedYouTubeTools
from assistant.agents.tools.thinking import EnhancedThinkingTools
from assistant.agents.tools.reasoning import EnhancedReasoningTools


arxiv = ArxivTools()
finance = EnhancedYFinanceTools()
wikipedia = WikipediaTools()
youtube = EnhancedYouTubeTools()
searxng = EnhancedSearxngTools(host="http://searxng:8080", max_results=10)
pubmed = PubmedTools()
wikipedia = WikipediaTools()
thinking = EnhancedThinkingTools()
reasoning = EnhancedReasoningTools()
calculator = CalculatorTools(enable_all=True)