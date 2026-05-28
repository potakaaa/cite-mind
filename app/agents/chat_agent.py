from typing import Any
from app.agents.base_agent import BaseAgent
from app.tools.academic_search import AcademicSearchTool
from app.tools.web_search import WebSearchTool


class ChatAgent(BaseAgent):
    """An autonomous agent for answering user queries and searching when needed."""

    def __init__(self, **kwargs: Any) -> None:
        tools = [AcademicSearchTool(), WebSearchTool()]
        super().__init__(name="chat_agent", tools=tools, **kwargs)

    def build_prompt(self, **kwargs: Any) -> str:
        # Prompt structure expects history and context from UI
        prompt = kwargs.get("prompt", "")
        return prompt
