from typing import List, Optional

from pydantic import BaseModel


# =====================================================
# BASIC NEWS REQUEST
# =====================================================

class NewsRequest(BaseModel):
    article: str


# =====================================================
# NEWS BRIEFING
# =====================================================

class NewsBriefing(BaseModel):
    headline: str
    summary: str
    what_happened: str
    why_it_matters: str
    key_facts: List[str]
    category: str
    confidence: str


# =====================================================
# DELTA / WHAT CHANGED
# =====================================================

class DeltaRequest(BaseModel):
    previous_news: str
    current_news: str


class DeltaResponse(BaseModel):
    what_changed: str
    new_information: List[str]
    confirmed_information: List[str]
    changed_information: List[str]
    corrected_information: List[str]
    still_uncertain: List[str]


# =====================================================
# EVIDENCE
# =====================================================

class EvidenceRequest(BaseModel):
    claim: str
    sources: List[str]


class EvidenceResponse(BaseModel):
    claim: str
    supporting_sources: List[str]
    contradicting_sources: List[str]
    neutral_sources: List[str]
    evidence_summary: str
    confidence: str
    confidence_reason: str


# =====================================================
# LIVING STORY REQUESTS
# =====================================================

class StoryCreateRequest(BaseModel):
    title: str
    article: str
    source_name: str = "Manual Source"


class StoryUpdateRequest(BaseModel):
    article: str
    source_name: str = "Manual Source"


# =====================================================
# LIVING STORY EVENT
# =====================================================

class StoryEvent(BaseModel):
    timestamp: str
    source_name: str
    article: str
    briefing: NewsBriefing
    delta: Optional[DeltaResponse] = None


# =====================================================
# LIVING STORY
# =====================================================

class LivingStory(BaseModel):
    story_id: str
    title: str
    category: str
    created_at: str
    updated_at: str
    latest_briefing: NewsBriefing
    latest_article: str
    total_updates: int
    timeline: List[StoryEvent]


# =====================================================
# COLLECTED NEWS ARTICLE
# =====================================================

class CollectedArticle(BaseModel):
    title: str
    summary: str
    source: str
    link: str
    published: str


class NewsCollectionResponse(BaseModel):
    total_articles: int
    articles: List[CollectedArticle]


# =====================================================
# STORY CLUSTERING
# =====================================================

class StoryCluster(BaseModel):
    cluster_id: int
    representative_title: str
    article_count: int
    articles: List[CollectedArticle]


class StoryClusteringResponse(BaseModel):
    total_articles: int
    total_clusters: int
    clusters: List[StoryCluster]


# =====================================================
# IMPACT
# =====================================================

class ImpactRequest(BaseModel):
    article: str
    user_role: str = "General Reader"


class ImpactGroup(BaseModel):
    group: str
    impact: str
    severity: str
    timeframe: str


class ImpactResponse(BaseModel):
    story_summary: str
    why_it_matters: str
    impact_level: str

    impacted_groups: List[ImpactGroup]

    direct_impact: List[str]
    indirect_impact: List[str]

    opportunities: List[str]
    risks: List[str]

    what_to_watch: List[str]

    user_specific_impact: str


# =====================================================
# SINGLE LANGCHAIN AGENT OUTPUT
# =====================================================

class SingleAgentAnalysis(BaseModel):
    briefing: NewsBriefing

    evidence: Optional[
        EvidenceResponse
    ] = None

    impact: ImpactResponse

    delta: Optional[
        DeltaResponse
    ] = None


# =====================================================
# ORCHESTRATOR REQUEST
# =====================================================

class OrchestratorRequest(BaseModel):
    user_role: str = "General Reader"
    limit_per_source: int = 3
    similarity_threshold: float = 0.50
    max_stories: int = 5


# =====================================================
# ORCHESTRATED STORY
# =====================================================

class OrchestratedStory(BaseModel):
    cluster_id: int
    representative_title: str
    article_count: int

    briefing: NewsBriefing

    evidence: Optional[
        EvidenceResponse
    ] = None

    evidence_note: str

    impact: ImpactResponse

    living_story_id: str

    memory_action: str

    memory_similarity: float

    delta: Optional[
        DeltaResponse
    ] = None

    sources: List[
        CollectedArticle
    ]


# =====================================================
# FINAL ORCHESTRATOR RESPONSE
# =====================================================

class OrchestratorResponse(BaseModel):
    agent_name: str

    total_articles_collected: int

    total_story_clusters: int

    analyzed_stories: int

    new_stories_created: int

    existing_stories_updated: int

    user_role: str

    stories: List[
        OrchestratedStory
    ]