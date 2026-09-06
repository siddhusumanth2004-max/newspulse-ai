import os
import re

from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate

from models.schemas import (
    NewsBriefing,
    EvidenceResponse,
    ImpactResponse,
    DeltaResponse,
    SingleAgentAnalysis,
)


# =========================================================
# ENVIRONMENT
# =========================================================

ENV_PATH = (
    Path(__file__)
    .resolve()
    .parent
    .parent
    / ".env"
)

load_dotenv(
    dotenv_path=ENV_PATH,
    override=True,
)


ANTHROPIC_API_KEY = os.getenv(
    "ANTHROPIC_API_KEY"
)

ANTHROPIC_MODEL = os.getenv(
    "ANTHROPIC_MODEL",
    "claude-haiku-4-5",
)


if not ANTHROPIC_API_KEY:
    raise ValueError(
        "ANTHROPIC_API_KEY is missing in ai_layer/.env"
    )


# =========================================================
# CLAUDE THROUGH LANGCHAIN
#
# temperature=0 gives more consistent structured output.
#
# Higher max_tokens prevents large structured responses
# from being cut before IMPACT is returned.
# =========================================================

llm = ChatAnthropic(
    model=ANTHROPIC_MODEL,
    temperature=0,
    max_tokens=6000,
)


# =========================================================
# ROLE GUIDANCE
# =========================================================

ROLE_GUIDANCE = {

    "Student": """
The supplied news was collected for students.

Focus only on student relevance supported by
the supplied material.

Possible areas include:
- education
- colleges
- universities
- examinations
- admissions
- scholarships
- internships
- careers
- skills
- student opportunities

Do not invent student effects.
""",

    "Developer": """
The supplied news was collected for developers.

Focus only on developer relevance supported by
the supplied material.

Possible areas include:
- programming
- software engineering
- APIs
- AI tools
- cloud
- cybersecurity
- developer platforms

Do not invent technical effects.
""",

    "Researcher": """
The supplied news was collected for researchers.

Focus on:
- evidence
- scientific relevance
- academic relevance
- research findings
- uncertainty
- unanswered questions

Do not invent research findings.
""",

    "Business Owner": """
The supplied news was collected for business owners.

Focus on:
- businesses
- operations
- customers
- markets
- regulation
- technology
- risks
- opportunities

Do not invent financial effects.
""",

    "General Reader": """
Explain the supplied story in clear everyday language.

Focus on:
- what happened
- why it matters
- important facts
- public relevance
""",
}


# =========================================================
# FULL NEWS INTELLIGENCE SYSTEM PROMPT
# =========================================================

SYSTEM_PROMPT = """
You are NewsPulse AI.

You are ONE unified AI News Briefing Agent.

NewsPulse has already collected the news.
You DO NOT search for additional information.

Use ONLY the supplied news material.


=========================================================
STRICT FACTUAL RULES
=========================================================

Never invent:

- facts
- people
- names
- dates
- numbers
- statistics
- quotes
- studies
- events
- predictions
- source positions

If the material is uncertain,
keep the answer uncertain.


=========================================================
REQUIRED TOP-LEVEL OUTPUT
=========================================================

The output MUST contain ALL FOUR top-level fields:

1. briefing
2. evidence
3. impact
4. delta


IMPORTANT:

impact is ALWAYS REQUIRED.

Never omit impact.

If evidence is not appropriate,
evidence must be null.

If delta is not appropriate,
delta must be null.


=========================================================
BRIEFING
=========================================================

briefing MUST contain:

- headline
- summary
- what_happened
- why_it_matters
- key_facts
- category
- confidence

confidence should be:

High
Medium
or Low


=========================================================
EVIDENCE
=========================================================

If at least two sources are supplied:

Analyze:
- main claim
- supporting sources
- contradicting sources
- neutral sources
- evidence summary
- confidence
- confidence reason

Use only publisher names present in
the supplied material.

If fewer than two sources exist:

evidence = null


=========================================================
IMPACT
=========================================================

impact MUST ALWAYS EXIST.

impact MUST contain:

- story_summary
- why_it_matters
- impact_level
- impacted_groups
- direct_impact
- indirect_impact
- opportunities
- risks
- what_to_watch
- user_specific_impact

If impact is unclear:

use cautious language.

Do NOT omit the impact object.


=========================================================
DELTA / WHAT CHANGED
=========================================================

If a previous Living Story exists:

compare the previous story with
the current story.

Return:

- what_changed
- new_information
- confirmed_information
- changed_information
- corrected_information
- still_uncertain

If no previous story exists:

delta = null


=========================================================
FINAL RULE
=========================================================

Follow the SingleAgentAnalysis schema exactly.

Never return briefing alone.

Never omit impact.
"""


# =========================================================
# USER PROMPT
# =========================================================

USER_PROMPT = """
SELECTED USER ROLE:

{user_role}


ROLE GUIDANCE:

{role_guidance}


NUMBER OF SOURCES:

{source_count}


STORY STATUS:

{story_status}


=========================================================
CURRENT NEWS MATERIAL
=========================================================

{story_context}


=========================================================
PREVIOUS LIVING STORY
=========================================================

{previous_story}


Create the complete NewsPulse analysis.

Remember:

briefing is required.
impact is required.
evidence may be null.
delta may be null.

Use only supplied information.
"""


# =========================================================
# FIRST FULL STRUCTURED CHAIN
# =========================================================

full_prompt = (
    ChatPromptTemplate.from_messages(
        [
            (
                "system",
                SYSTEM_PROMPT,
            ),
            (
                "human",
                USER_PROMPT,
            ),
        ]
    )
)


full_structured_llm = (
    llm.with_structured_output(
        SingleAgentAnalysis
    )
)


full_chain = (
    full_prompt
    |
    full_structured_llm
)


# =========================================================
# REPAIR PROMPT
#
# Used only if Claude returns malformed structured output.
# =========================================================

REPAIR_SYSTEM_PROMPT = (
    SYSTEM_PROMPT
    +
    """

=========================================================
STRUCTURE REPAIR MODE
=========================================================

A previous response failed schema validation.

This attempt MUST fix the structure.

The response MUST contain:

briefing
evidence
impact
delta

impact MUST NOT be omitted.

Return a complete SingleAgentAnalysis object.
"""
)


repair_prompt = (
    ChatPromptTemplate.from_messages(
        [
            (
                "system",
                REPAIR_SYSTEM_PROMPT,
            ),
            (
                "human",
                USER_PROMPT,
            ),
        ]
    )
)


repair_chain = (
    repair_prompt
    |
    full_structured_llm
)


# =========================================================
# BRIEFING FALLBACK CHAIN
# =========================================================

BRIEFING_SYSTEM_PROMPT = """
You are the NewsPulse News Briefing component.

Use ONLY the supplied news.

Return a NewsBriefing object containing:

headline
summary
what_happened
why_it_matters
key_facts
category
confidence

Do not invent facts.
"""


briefing_prompt = (
    ChatPromptTemplate.from_messages(
        [
            (
                "system",
                BRIEFING_SYSTEM_PROMPT,
            ),
            (
                "human",
                USER_PROMPT,
            ),
        ]
    )
)


briefing_chain = (
    briefing_prompt
    |
    llm.with_structured_output(
        NewsBriefing
    )
)


# =========================================================
# IMPACT FALLBACK CHAIN
# =========================================================

IMPACT_SYSTEM_PROMPT = """
You are the NewsPulse Impact Analysis component.

Use ONLY the supplied news.

Return a complete ImpactResponse object.

It MUST contain:

story_summary
why_it_matters
impact_level
impacted_groups
direct_impact
indirect_impact
opportunities
risks
what_to_watch
user_specific_impact

Do not invent facts.

Use cautious language when impact is uncertain.
"""


impact_prompt = (
    ChatPromptTemplate.from_messages(
        [
            (
                "system",
                IMPACT_SYSTEM_PROMPT,
            ),
            (
                "human",
                USER_PROMPT,
            ),
        ]
    )
)


impact_chain = (
    impact_prompt
    |
    llm.with_structured_output(
        ImpactResponse
    )
)


# =========================================================
# EVIDENCE FALLBACK CHAIN
# =========================================================

EVIDENCE_SYSTEM_PROMPT = """
You are the NewsPulse Evidence Analysis component.

Use ONLY the supplied source material.

Return an EvidenceResponse object.

Use only source/publisher names contained
in the supplied material.

Do not invent evidence.
"""


evidence_prompt = (
    ChatPromptTemplate.from_messages(
        [
            (
                "system",
                EVIDENCE_SYSTEM_PROMPT,
            ),
            (
                "human",
                USER_PROMPT,
            ),
        ]
    )
)


evidence_chain = (
    evidence_prompt
    |
    llm.with_structured_output(
        EvidenceResponse
    )
)


# =========================================================
# DELTA FALLBACK CHAIN
# =========================================================

DELTA_SYSTEM_PROMPT = """
You are the NewsPulse Living Story Change component.

Compare ONLY the supplied previous and current story.

Return a DeltaResponse object containing:

what_changed
new_information
confirmed_information
changed_information
corrected_information
still_uncertain

Do not invent changes.
"""


delta_prompt = (
    ChatPromptTemplate.from_messages(
        [
            (
                "system",
                DELTA_SYSTEM_PROMPT,
            ),
            (
                "human",
                USER_PROMPT,
            ),
        ]
    )
)


delta_chain = (
    delta_prompt
    |
    llm.with_structured_output(
        DeltaResponse
    )
)


# =========================================================
# ROLE HELPER
# =========================================================

def get_role_guidance(
    user_role: str,
) -> str:

    selected_role = (
        user_role
        or "General Reader"
    ).strip()

    return ROLE_GUIDANCE.get(
        selected_role,
        ROLE_GUIDANCE[
            "General Reader"
        ],
    )


# =========================================================
# EXTRACT FIRST SOURCE HEADLINE
#
# Only used for emergency fallback.
# =========================================================

def extract_first_headline(
    story_context: str,
) -> str:

    match = re.search(
        r"(?im)^Headline:\s*(.+)$",
        story_context or "",
    )

    if match:

        return (
            match.group(1)
            .strip()[:250]
        )

    return "News update"


# =========================================================
# EXTRACT FIRST SOURCE SUMMARY
# =========================================================

def extract_first_summary(
    story_context: str,
) -> str:

    match = re.search(
        r"(?ims)^Summary:\s*(.+?)(?:\n\n|\nPublished:|\Z)",
        story_context or "",
    )

    if match:

        summary = (
            match.group(1)
            .strip()
        )

        return summary[:700]

    return ""


# =========================================================
# EMERGENCY BRIEFING
#
# This guarantees Pydantic always receives
# a valid NewsBriefing object.
# =========================================================

def build_emergency_briefing(
    story_context: str,
) -> NewsBriefing:

    headline = extract_first_headline(
        story_context
    )

    source_summary = (
        extract_first_summary(
            story_context
        )
    )

    if source_summary:

        summary = source_summary

        what_happened = (
            source_summary
        )

    else:

        summary = (
            "NewsPulse collected this story, "
            "but the AI response could not be "
            "converted into the required "
            "structured briefing."
        )

        what_happened = (
            headline
        )

    return NewsBriefing(
        headline=headline,

        summary=summary,

        what_happened=(
            what_happened
        ),

        why_it_matters=(
            "NewsPulse could not reliably "
            "generate a complete interpretation "
            "for this story. Review the supplied "
            "source information."
        ),

        key_facts=[],

        category="General",

        confidence="Low",
    )


# =========================================================
# EMERGENCY IMPACT
#
# IMPORTANT:
# This prevents the exact current crash:
#
# SingleAgentAnalysis -> impact -> Field required
# =========================================================

def build_emergency_impact(
    user_role: str,
) -> ImpactResponse:

    return ImpactResponse(
        story_summary=(
            "A reliable structured impact "
            "analysis could not be generated "
            "from the AI response."
        ),

        why_it_matters=(
            "The source material should be "
            "reviewed before drawing conclusions "
            "about real-world impact."
        ),

        impact_level="Unknown",

        impacted_groups=[],

        direct_impact=[],

        indirect_impact=[],

        opportunities=[],

        risks=[],

        what_to_watch=[],

        user_specific_impact=(
            f"No reliable {user_role} specific "
            "impact could be generated from the "
            "supplied material."
        ),
    )


# =========================================================
# NORMALIZE RESULT
# =========================================================

def normalize_analysis(
    analysis: SingleAgentAnalysis,
    source_count: int,
    has_previous_story: bool,
) -> SingleAgentAnalysis:

    # -----------------------------------------------------
    # ONE SOURCE = NO MULTI-SOURCE EVIDENCE
    # -----------------------------------------------------

    if source_count < 2:

        analysis.evidence = None


    # -----------------------------------------------------
    # NEW STORY = NO DELTA
    # -----------------------------------------------------

    if not has_previous_story:

        analysis.delta = None


    return analysis


# =========================================================
# COMPONENT FALLBACK
#
# Used only after BOTH full structured attempts fail.
# =========================================================

def generate_component_fallback(
    payload: dict,
    story_context: str,
    user_role: str,
    source_count: int,
    has_previous_story: bool,
) -> SingleAgentAnalysis:

    print()
    print(
        "[AI FALLBACK] "
        "Generating components separately..."
    )


    # =====================================================
    # BRIEFING
    # =====================================================

    try:

        briefing = (
            briefing_chain.invoke(
                payload
            )
        )

        print(
            "[AI FALLBACK] "
            "Briefing OK"
        )

    except Exception as error:

        print(
            "[AI FALLBACK] "
            "Briefing failed:",
            str(error)[:300]
        )

        briefing = (
            build_emergency_briefing(
                story_context
            )
        )


    # =====================================================
    # IMPACT
    # =====================================================

    try:

        impact = (
            impact_chain.invoke(
                payload
            )
        )

        print(
            "[AI FALLBACK] "
            "Impact OK"
        )

    except Exception as error:

        print(
            "[AI FALLBACK] "
            "Impact failed:",
            str(error)[:300]
        )

        impact = (
            build_emergency_impact(
                user_role
            )
        )


    # =====================================================
    # EVIDENCE
    # =====================================================

    evidence = None

    if source_count >= 2:

        try:

            evidence = (
                evidence_chain.invoke(
                    payload
                )
            )

            print(
                "[AI FALLBACK] "
                "Evidence OK"
            )

        except Exception as error:

            print(
                "[AI FALLBACK] "
                "Evidence skipped:",
                str(error)[:300]
            )

            evidence = None


    # =====================================================
    # DELTA
    # =====================================================

    delta = None

    if has_previous_story:

        try:

            delta = (
                delta_chain.invoke(
                    payload
                )
            )

            print(
                "[AI FALLBACK] "
                "Delta OK"
            )

        except Exception as error:

            print(
                "[AI FALLBACK] "
                "Delta skipped:",
                str(error)[:300]
            )

            delta = None


    # =====================================================
    # GUARANTEED VALID FINAL OBJECT
    # =====================================================

    return SingleAgentAnalysis(
        briefing=briefing,
        evidence=evidence,
        impact=impact,
        delta=delta,
    )


# =========================================================
# MAIN FUNCTION
#
# orchestrator_agent.py imports this exact function.
# =========================================================

def analyze_news_story(
    story_context: str,
    user_role: str,
    source_count: int,
    previous_story: Optional[str] = None,
) -> SingleAgentAnalysis:

    selected_role = (
        user_role
        or "General Reader"
    ).strip()


    role_guidance = (
        get_role_guidance(
            selected_role
        )
    )


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
            "No previous Living Story exists."
        )


    payload = {
        "user_role":
            selected_role,

        "role_guidance":
            role_guidance,

        "source_count":
            source_count,

        "story_status":
            story_status,

        "story_context":
            story_context,

        "previous_story":
            previous_story_text,
    }


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
        "Role:",
        selected_role
    )

    print(
        "Sources:",
        source_count
    )

    print(
        "Story status:",
        story_status
    )


    # =====================================================
    # ATTEMPT 1
    #
    # Fast normal one-call path.
    # =====================================================

    try:

        analysis = (
            full_chain.invoke(
                payload
            )
        )

        analysis = (
            normalize_analysis(
                analysis=analysis,

                source_count=
                    source_count,

                has_previous_story=
                    has_previous_story,
            )
        )

        print(
            "[AI] Full structured "
            "analysis successful."
        )

        return analysis


    except Exception as first_error:

        print()
        print(
            "[AI WARNING] "
            "First structured response failed."
        )

        print(
            str(first_error)[:500]
        )


    # =====================================================
    # ATTEMPT 2
    #
    # Same schema with stronger structure instructions.
    # =====================================================

    try:

        print()
        print(
            "[AI RETRY] "
            "Retrying complete structured output..."
        )

        analysis = (
            repair_chain.invoke(
                payload
            )
        )

        analysis = (
            normalize_analysis(
                analysis=analysis,

                source_count=
                    source_count,

                has_previous_story=
                    has_previous_story,
            )
        )

        print(
            "[AI RETRY] "
            "Structured retry successful."
        )

        return analysis


    except Exception as retry_error:

        print()
        print(
            "[AI WARNING] "
            "Structured retry failed."
        )

        print(
            str(retry_error)[:500]
        )


    # =====================================================
    # FINAL FALLBACK
    #
    # Instead of causing HTTP 500,
    # build each component independently.
    # =====================================================

    analysis = (
        generate_component_fallback(
            payload=payload,

            story_context=
                story_context,

            user_role=
                selected_role,

            source_count=
                source_count,

            has_previous_story=
                has_previous_story,
        )
    )


    analysis = (
        normalize_analysis(
            analysis=analysis,

            source_count=
                source_count,

            has_previous_story=
                has_previous_story,
        )
    )


    print()
    print(
        "[AI] Fallback analysis complete."
    )

    print(
        "========================================"
    )


    return analysis