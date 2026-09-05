import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate

from models.schemas import ImpactResponse


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
    max_tokens=1800,
)

structured_model = model.with_structured_output(
    ImpactResponse
)

prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are the Impact Agent inside NewsPulse AI.

Understand the real-world impact of a news story. Do not simply summarize it.

Analyze:
- why the story matters
- who is affected
- severity and timeframe
- direct impacts
- possible indirect impacts
- opportunities
- risks
- what to watch next
- how the story matters to the selected user role

Rules:
- Do not invent facts.
- Separate facts from possible future effects.
- Future effects must be described as possibilities, not certainties.
- Keep the language simple.
- Impact level and severity must be High, Medium, or Low.
- The response must match the requested structured schema.""",
        ),
        (
            "human",
            "USER ROLE:\n{user_role}\n\nNEWS:\n\n{article}",
        ),
    ]
)

chain = prompt | structured_model


# =====================================================
# IMPACT AGENT
# =====================================================

def analyze_impact(
    article: str,
    user_role: str,
) -> ImpactResponse:
    return chain.invoke(
        {
            "article": article,
            "user_role": user_role,
        }
    )
