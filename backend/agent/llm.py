import os

from dotenv import load_dotenv
from agno.models.openai import OpenAIChat

load_dotenv()

# Calling API key.
_BASE = os.environ["LLM_REST_URL"].removesuffix("/chat/completions")


def make_llm() -> OpenAIChat:
    # Build an Agno OpenAI model pointed at the Navigator endpoint.
    return OpenAIChat(
        id=os.environ["MODEL_NAME"],
        api_key=os.environ["LLM_API_KEY"],
        base_url=_BASE,
        timeout=float(os.environ.get("LLM_TIMEOUT_SECONDS", 30)),
        max_retries=int(os.environ.get("LLM_MAX_RETRIES", 2)),
    )
