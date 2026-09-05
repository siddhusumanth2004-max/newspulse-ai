import os

from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from langchain_anthropic import ChatAnthropic

from langchain_core.prompts import (
    ChatPromptTemplate
)

from models.schemas import (
    SingleAgentAnalysis
)


# =====================================================
# ENVIRONMENT
# =====================================================

ENV_PATH = (
    Path(__file__)
    .resolve()
    .parent
    .parent
    / ".env"
)


load_dotenv(
    dotenv_path=ENV_PATH,
    override=True
)


ANTHROPIC_API_KEY = os.getenv(
    "ANTHROPIC_API_KEY"
)


ANTHROPIC_MODEL = os.getenv(
    "ANTHROPIC_MODEL",
    "claude-haiku-4-5"
)


if not ANTHROPIC_API_KEY:

    raise ValueError(
        "ANTHROPIC_API_KEY is missing "
        "inside ai_layer/.env"
    )


# =====================================================
# LANGCHAIN MODEL
# =====================================================

llm = ChatAnthropic(

    model=ANTHROPIC_MODEL,

    temperature=0.2,

    max_tokens=5000

)


# =====================================================
# PYDANTIC STRUCTURED OUTPUT
# =====================================================

structured_llm = (
    llm.with_structured_output(
        SingleAgentAnalysis
    )
)


# =====================================================
# SYSTEM PROMPT
# =====================================================

SYSTEM_PROMPT = """
You are NewsPulse AI.

You are ONE unified News Intelligence Agent.

Your central purpose is:

"Don't repeat the news.
Tell the user what changed."

You analyze one news story at a time.

You perform four responsibilities:

1. NEWS BRIEFING
2. EVIDENCE ANALYSIS
3. REAL-WORLD IMPACT ANALYSIS
4. LIVING STORY CHANGE DETECTION


=====================================================
GENERAL RULES
=====================================================

Only use information supplied in the news material.

Never invent:

- facts
- names
- quotes
- numbers
- dates
- statistics
- source positions
- events
- predictions

If something is uncertain,
describe it as uncertain.

Do not present speculation as fact.

Use simple and useful language.


=====================================================
BRIEFING
=====================================================

Create:

- headline
- summary
- what happened
- why it matters
- key facts
- category
- confidence


Confidence should be:

High
Medium
or
Low


=====================================================
EVIDENCE
=====================================================

When multiple sources are supplied:

Identify:

- supporting sources
- contradicting sources
- neutral sources
- evidence summary
- confidence
- confidence reason

Do not assume two articles are
independent confirmation simply
because they repeat the same claim.

Use the supplied publisher/source
labels when describing evidence.


When fewer than two sources exist:

evidence must be null.


=====================================================
IMPACT
=====================================================

Analyze:

- overall impact level
- groups affected
- direct impact
- indirect impact
- opportunities
- risks
- what to watch
- user-specific impact

Do not exaggerate impact.

Separate direct effects from
possible future effects.


=====================================================
LIVING STORY / DELTA
=====================================================

If a previous version exists:

Compare it with the current story.

Explain:

- what changed
- genuinely new information
- newly confirmed information
- changed information
- corrected information
- remaining uncertainty


If this is a new story:

delta must be null.


=====================================================
OUTPUT
=====================================================

Return the structured NewsPulse result
required by the supplied schema.
"""


# =====================================================
# USER PROMPT
# =====================================================

USER_PROMPT = """
USER ROLE:

{user_role}


NUMBER OF CURRENT SOURCES:

{source_count}


STORY STATUS:

{story_status}


=====================================================
CURRENT NEWS MATERIAL
=====================================================

{story_context}


=====================================================
PREVIOUS LIVING STORY
=====================================================

{previous_story}


Analyze this story.

Create:

- briefing
- evidence when appropriate
- impact analysis
- delta when appropriate

Personalize the impact explanation
for the supplied user role.
"""


# =====================================================
# LANGCHAIN PROMPT TEMPLATE
# =====================================================

prompt_template = (
    ChatPromptTemplate.from_messages(
        [
            (
                "system",
                SYSTEM_PROMPT
            ),

            (
                "human",
                USER_PROMPT
            )
        ]
    )
)


# =====================================================
# LANGCHAIN CHAIN
#
# Prompt
#   ↓
# Claude
#   ↓
# Structured Pydantic Output
# =====================================================

news_intelligence_chain = (

    prompt_template

    |

    structured_llm

)


# =====================================================
# SINGLE NEWS INTELLIGENCE AGENT
# =====================================================

def analyze_news_story(
    story_context: str,
    user_role: str,
    source_count: int,
    previous_story: Optional[str] = None
) -> SingleAgentAnalysis:

    has_previous_story = bool(

        previous_story

        and

        previous_story.strip()

    )


    if has_previous_story:

        story_status = (
            "EXISTING LIVING STORY"
        )

        previous_story_text = (
            previous_story
        )

    else:

        story_status = (
            "NEW STORY"
        )

        previous_story_text = (
            "No previous version exists."
        )


    print()

    print(
        "========================================"
    )

    print(
        "LANGCHAIN NEWS INTELLIGENCE AGENT"
    )

    print(
        "========================================"
    )

    print(
        "Model:",
        ANTHROPIC_MODEL
    )

    print(
        "Story status:",
        story_status
    )

    print(
        "Sources:",
        source_count
    )


    # =================================================
    # RUN LANGCHAIN
    # =================================================

    analysis = (
        news_intelligence_chain.invoke(
            {
                "user_role":
                    user_role,

                "source_count":
                    source_count,

                "story_status":
                    story_status,

                "story_context":
                    story_context,

                "previous_story":
                    previous_story_text
            }
        )
    )


    # =================================================
    # LOCAL CONSISTENCY RULE
    # ONE SOURCE = NO MULTI-SOURCE EVIDENCE
    # =================================================

    if source_count < 2:

        analysis.evidence = None


    # =================================================
    # LOCAL CONSISTENCY RULE
    # NEW STORY = NO DELTA
    # =================================================

    if not has_previous_story:

        analysis.delta = None


    print(
        "LangChain analysis complete."
    )


    return analysis