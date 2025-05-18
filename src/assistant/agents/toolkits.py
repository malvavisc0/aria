from agno.tools.arxiv import ArxivTools
from agno.tools.pubmed import PubmedTools
from agno.tools.reasoning import ReasoningTools  # broken
from agno.tools.thinking import ThinkingTools
from agno.tools.wikipedia import WikipediaTools

from assistant.agents.tools.finance import YFinanceTools
from assistant.agents.tools.searxng import SearxngTools
from assistant.agents.tools.youtube import YouTubeTools

_THINKING_INSTRUCTIONS = """
## Using the think tool
Before replying or taking the next step, use the think tool to quietly gather your thoughts. This can include:
 - Jotting down any relevant rules or info you remember
 - Noting if you're missing anything important to answer well
 - Checking if your next step makes sense and follows guidelines
 - Reflecting on any uncertainties or alternative ideas that come up
 - Feel free to think out loud — keep it brief, informal, and honest, like how a human might reflect silently before answering

## Rules
- Use the think tool as much as you can
- Do not return your thoughts in the response
"""

arxiv = ArxivTools()
finance = YFinanceTools()
wikipedia = WikipediaTools()
youtube = YouTubeTools()
searxng = SearxngTools(host="http://searxng:8080", max_results=50)
pubmed = PubmedTools()
wikipedia = WikipediaTools()
thinking = ThinkingTools(
    instructions=_THINKING_INSTRUCTIONS, add_instructions=True
)

reasoning = ReasoningTools()  # broken
