from __future__ import annotations

from abc import ABC, abstractmethod
import json
from typing import Any

from app.llm.base_provider import LLMProviderError, LLMResponse
from app.llm.llm_router import LLMRouter
from app.tools.base import BaseTool
from app.utils.logging import get_logger, log_failure


class AgentExecutionError(RuntimeError):
    """Raised when agent execution fails."""


class BaseAgent(ABC):
    """Reusable base class for all agents with shared LLM execution flow."""

    def __init__(
        self, 
        name: str, 
        llm: LLMRouter | None = None, 
        prompt_template: str = "",
        tools: list[BaseTool] | None = None
    ) -> None:
        self.name = name
        self.llm = llm or LLMRouter()
        self.prompt_template = prompt_template
        self.tools = tools or []
        self.logger = get_logger(f"app.agents.{self.name}")

    @abstractmethod
    def build_prompt(self, **kwargs: Any) -> str:
        """Build the final prompt from input data. Override in child agents."""

    def handle_response(self, response: str) -> Any:
        """Optional post-processing hook for child agents."""
        return response

    def run(self, provider: str | None = None, task_type: str | None = None, **kwargs: Any) -> Any:
        """Run agent flow: prompt build -> LLM call -> response handling."""
        self.logger.info("Agent '%s' started", self.name)

        try:
            prompt = self.build_prompt(**kwargs)
            if not isinstance(prompt, str) or not prompt.strip():
                raise AgentExecutionError(
                    f"Agent '{self.name}' built an empty or invalid prompt."
                )

            messages = [{"role": "user", "content": prompt}]
            
            # Tool Execution Loop
            while True:
                response: LLMResponse = self.llm.generate(
                    prompt=prompt, # Kept for fallback/logging, but messages overrides it
                    provider=provider,
                    task_type=task_type,
                    tools=self.tools,
                    messages=messages,
                )
                
                if not response.tool_calls:
                    raw_response = response.text
                    break
                    
                # Append assistant's tool call intent
                messages.append({
                    "role": "assistant",
                    "content": response.text,
                    "tool_calls": [
                        {
                            "type": "function",
                            "function": {
                                "name": tc.name,
                                "arguments": json.dumps(tc.arguments)
                            }
                        }
                        for tc in response.tool_calls
                    ]
                })
                
                # Execute tools
                for tc in response.tool_calls:
                    self.logger.info(f"Agent '{self.name}' calling tool '{tc.name}' with args {tc.arguments}")
                    tool_obj = next((t for t in self.tools if t.name == tc.name), None)
                    
                    if tool_obj:
                        try:
                            result = tool_obj.execute(**tc.arguments)
                            result_str = json.dumps(result)
                        except Exception as e:
                            self.logger.error(f"Tool {tc.name} failed: {e}")
                            result_str = f"Error executing tool: {e}"
                    else:
                        result_str = f"Error: Tool {tc.name} not found."
                        
                    # Append tool result
                    messages.append({
                        "role": "tool",
                        "name": tc.name,
                        "content": result_str
                    })

            parsed = self.handle_response(raw_response)

            self.logger.info("Agent '%s' finished", self.name)
            return parsed
        except (LLMProviderError, AgentExecutionError, ValueError, TypeError) as exc:
            log_failure(self.logger, "agent_execution", exc, agent=self.name, task_type=task_type)
            raise AgentExecutionError(f"Agent '{self.name}' failed: {exc}") from exc
