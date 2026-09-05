import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate

from models.schemas import DeltaResponse


# =====================================================
# ENVIRONMENT
# =====================================================

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"

load_dotenv(
    dotenv_path=ENV_PATH,
    override=True,
)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = os.getenv(
    "ANTHROPIC_MODEL",
    "claude-haiku-4-5",
)

if not ANTHROPIC_API_KEY:
    raise ValueError(
        f"ANTHROPIC_API_KEY is missing in {ENV_PATH}"
    )


# =====================================================
# LANGCHAIN MODEL + STRUCTURED OUTPUT
# =====================================================

model = ChatAnthropic(
    model=ANTHROPIC_MODEL,
    temperature=0.1,
    max_tokens=1400,
)

structured_model = model.with_structured_output(
    DeltaResponse
)

prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are the Delta Agent inside an AI News Briefing System.

Compare OLD NEWS with NEW NEWS. Do not simply summarize both articles.

Identify:
1. New information
2. Confirmed information
3. Changed information
4. Corrected information
5. Still uncertain information

Rules:
- Do not invent information.
- Only compare information present in the supplied news.
- If a category has no information, return an empty list.
- The response must match the requested structured schema.""",
        ),
        (
            "human",
            "OLD NEWS:\n\n{previous_news}\n\nNEW NEWS:\n\n{current_news}",
        ),
    ]
)

chain = prompt | structured_model


# =====================================================
# DELTA AGENT
# =====================================================

def detect_changes(
    previous_news: str,
    current_news: str,
) -> DeltaResponse:
    return chain.invoke(
        {
            "previous_news": previous_news,
            "current_news": current_news,
        }
    )
