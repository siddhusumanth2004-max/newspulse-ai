import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate

from models.schemas import NewsBriefing


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
    temperature=0.2,
    max_tokens=1200,
)

structured_model = model.with_structured_output(
    NewsBriefing
)

prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are an AI News Briefing Agent.

Your job is to read the supplied news article carefully and create a clear, factual, simple briefing.

Rules:
- Do not invent information.
- Only use information available in the article.
- Keep the explanation simple.
- Choose category from: Technology, Business, Sports, Politics, Science, Entertainment, Other.
- Confidence must be High, Medium, or Low.
- Return the structured fields requested by the schema.""",
        ),
        (
            "human",
            "NEWS ARTICLE:\n\n{article}",
        ),
    ]
)

chain = prompt | structured_model


# =====================================================
# NEWS BRIEFING AGENT
# =====================================================

def generate_briefing(article: str) -> NewsBriefing:
    return chain.invoke(
        {
            "article": article,
        }
    )
