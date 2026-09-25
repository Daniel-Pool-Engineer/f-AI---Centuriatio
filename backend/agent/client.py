from typing import Dict, List

from agno.agent import Agent

from backend.agent.llm import make_llm


class LLMClient:
    def __init__(self) -> None:
        self._agent = Agent(
            model=make_llm(),
            markdown=False,
            telemetry=False,
        )

    def chat(self, messages: List[Dict[str, str]]) -> str:
        system = next((m["content"] for m in messages if m["role"] == "system"), "")
        user = next((m["content"] for m in messages if m["role"] == "user"), "")

        response = self._agent.run(
            input=f"{system}\n\n{user}",
            stream=False,
        )

        return response.content
