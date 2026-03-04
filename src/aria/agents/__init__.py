from .aria import ChatterAgent
from .aria import get_agent as get_chatter_agent
from .guido import PythonDeveloperAgent
from .guido import get_agent as get_python_developer_agent
from .prompt_enhancer import PromptEnhancerAgent
from .prompt_enhancer import get_agent as get_prompt_enhancer_agent
from .socrates import DeepReasoningAgent
from .socrates import get_agent as get_reasoning_agent
from .spielberg import IMDbExpertAgent
from .spielberg import get_agent as get_imdb_exper_agent
from .stallman import ShellExecutorAgent
from .stallman import get_agent as get_shell_executor_agent
from .wanderer import WebResearcherAgent
from .wanderer import get_agent as get_web_researcher_agent
from .wizard import MarketAnalystAgent
from .wizard import get_agent as get_market_analyst_agent

__all__ = [
    "IMDbExpertAgent",
    "PythonDeveloperAgent",
    "PromptEnhancerAgent",
    "DeepReasoningAgent",
    "MarketAnalystAgent",
    "WebResearcherAgent",
    "ChatterAgent",
    "ShellExecutorAgent",
    "get_python_developer_agent",
    "get_reasoning_agent",
    "get_prompt_enhancer_agent",
    "get_market_analyst_agent",
    "get_web_researcher_agent",
    "get_chatter_agent",
    "get_shell_executor_agent",
    "get_imdb_exper_agent",
]
