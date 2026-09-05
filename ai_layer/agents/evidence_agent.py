import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate

from models.schemas import EvidenceResponse


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
    EvidenceResponse
)

prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are the Evidence Agent inside an AI News Briefing System.

Check whether the supplied news sources support, contradict, or remain neutral about the claim.

Rules:
- Do not invent facts.
- Only use the supplied sources.
- Refer to sources using labels such as Source 1, Source 2, Source 3.
- Do not claim independent confirmation when sources merely repeat the same underlying report.
- Confidence must be High, Medium, or Low.
- The response must match the requested structured schema.""",
        ),
        (
            "human",
            "CLAIM:\n\n{claim}\n\nSOURCES:\n\n{sources_text}",
        ),
    ]
)

chain = prompt | structured_model


# =====================================================
# EVIDENCE AGENT
# =====================================================

def analyze_evidence(
    claim: str,
    sources: list[str],
) -> EvidenceResponse:
    sources_text = "\n\n".join(
        f"SOURCE {index}:\n{source}"
        for index, source in enumerate(
            sources,
            start=1,
        )
    )

    return chain.invoke(
        {
            "claim": claim,
            "sources_text": sources_text,
        }
    )
