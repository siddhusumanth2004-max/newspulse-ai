from typing import List

from fastapi import (
    FastAPI,
    HTTPException,
    Query
)

from models.schemas import (
    NewsRequest,
    NewsBriefing,

    DeltaRequest,
    DeltaResponse,

    EvidenceRequest,
    EvidenceResponse,

    ImpactRequest,
    ImpactResponse,

    StoryCreateRequest,
    StoryUpdateRequest,
    LivingStory,

    NewsCollectionResponse,
    StoryClusteringResponse,

    OrchestratorRequest,
    OrchestratorResponse
)

from agents.briefing_agent import (
    generate_briefing
)

from agents.delta_agent import (
    detect_changes
)

from agents.evidence_agent import (
    analyze_evidence
)

from agents.impact_agent import (
    analyze_impact
)

from agents.orchestrator_agent import (
    run_orchestrator
)

from services.story_memory import (
    create_story,
    get_story,
    get_all_stories,
    update_story
)

from services.news_collector import (
    collect_latest_news
)

from services.story_cluster import (
    cluster_articles
)


# =====================================================
# FASTAPI APPLICATION
# =====================================================

app = FastAPI(
    title="NewsPulse AI",
    description=(
        "Living News Briefing Agent with "
        "multi-source collection, semantic clustering, "
        "briefing, evidence verification, impact analysis, "
        "story memory and orchestration."
    ),
    version="6.0.0"
)


# =====================================================
# HOME
# =====================================================

@app.get("/")
def home():

    return {
        "message": "NewsPulse AI is running",
        "status": "success",
        "version": "6.0.0"
    }


# =====================================================
# HEALTH
# =====================================================

@app.get("/health")
def health():

    return {
        "status": "healthy",
        "service": "newspulse-ai-layer"
    }


# =====================================================
# ORCHESTRATOR AGENT
# =====================================================

@app.post(
    "/orchestrate",
    response_model=OrchestratorResponse
)
def orchestrate_news(
    request: OrchestratorRequest
):

    try:

        if request.limit_per_source < 1:

            raise HTTPException(
                status_code=400,
                detail=(
                    "limit_per_source must be "
                    "at least 1"
                )
            )


        if request.max_stories < 1:

            raise HTTPException(
                status_code=400,
                detail=(
                    "max_stories must be "
                    "at least 1"
                )
            )


        if not (
            0.40
            <= request.similarity_threshold
            <= 0.95
        ):

            raise HTTPException(
                status_code=400,
                detail=(
                    "similarity_threshold must "
                    "be between 0.40 and 0.95"
                )
            )


        return run_orchestrator(
            user_role=request.user_role,

            limit_per_source=(
                request.limit_per_source
            ),

            similarity_threshold=(
                request.similarity_threshold
            ),

            max_stories=(
                request.max_stories
            )
        )


    except HTTPException:
        raise


    except Exception as error:

        print(
            "ORCHESTRATOR ERROR:",
            error
        )

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


# =====================================================
# BRIEFING AGENT
# =====================================================

@app.post(
    "/brief",
    response_model=NewsBriefing
)
def create_briefing(
    request: NewsRequest
):

    try:

        if not request.article.strip():

            raise HTTPException(
                status_code=400,
                detail="Article cannot be empty"
            )

        return generate_briefing(
            request.article
        )


    except HTTPException:
        raise


    except Exception as error:

        print(
            "BRIEFING AGENT ERROR:",
            error
        )

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


# =====================================================
# DELTA AGENT
# =====================================================

@app.post(
    "/delta",
    response_model=DeltaResponse
)
def compare_news(
    request: DeltaRequest
):

    try:

        if not request.previous_news.strip():

            raise HTTPException(
                status_code=400,
                detail="Previous news cannot be empty"
            )


        if not request.current_news.strip():

            raise HTTPException(
                status_code=400,
                detail="Current news cannot be empty"
            )


        return detect_changes(
            previous_news=request.previous_news,
            current_news=request.current_news
        )


    except HTTPException:
        raise


    except Exception as error:

        print(
            "DELTA AGENT ERROR:",
            error
        )

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


# =====================================================
# EVIDENCE AGENT
# =====================================================

@app.post(
    "/evidence",
    response_model=EvidenceResponse
)
def check_evidence(
    request: EvidenceRequest
):

    try:

        if not request.claim.strip():

            raise HTTPException(
                status_code=400,
                detail="Claim cannot be empty"
            )


        if len(request.sources) < 2:

            raise HTTPException(
                status_code=400,
                detail=(
                    "At least 2 sources are required"
                )
            )


        return analyze_evidence(
            claim=request.claim,
            sources=request.sources
        )


    except HTTPException:
        raise


    except Exception as error:

        print(
            "EVIDENCE AGENT ERROR:",
            error
        )

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


# =====================================================
# IMPACT AGENT
# =====================================================

@app.post(
    "/impact",
    response_model=ImpactResponse
)
def get_news_impact(
    request: ImpactRequest
):

    try:

        if not request.article.strip():

            raise HTTPException(
                status_code=400,
                detail="Article cannot be empty"
            )


        return analyze_impact(
            article=request.article,
            user_role=request.user_role
        )


    except HTTPException:
        raise


    except Exception as error:

        print(
            "IMPACT AGENT ERROR:",
            error
        )

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


# =====================================================
# CREATE LIVING STORY
# =====================================================

@app.post(
    "/stories",
    response_model=LivingStory
)
def create_living_story(
    request: StoryCreateRequest
):

    try:

        if not request.title.strip():

            raise HTTPException(
                status_code=400,
                detail="Story title cannot be empty"
            )


        if not request.article.strip():

            raise HTTPException(
                status_code=400,
                detail="Article cannot be empty"
            )


        return create_story(
            title=request.title,
            article=request.article,
            source_name=request.source_name
        )


    except HTTPException:
        raise


    except Exception as error:

        print(
            "CREATE STORY ERROR:",
            error
        )

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


# =====================================================
# GET ALL LIVING STORIES
# =====================================================

@app.get(
    "/stories",
    response_model=List[LivingStory]
)
def list_living_stories():

    try:

        return get_all_stories()


    except Exception as error:

        print(
            "GET STORIES ERROR:",
            error
        )

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


# =====================================================
# GET ONE LIVING STORY
# =====================================================

@app.get(
    "/stories/{story_id}",
    response_model=LivingStory
)
def read_living_story(
    story_id: str
):

    try:

        story = get_story(
            story_id
        )


        if not story:

            raise HTTPException(
                status_code=404,
                detail="Story not found"
            )


        return story


    except HTTPException:
        raise


    except Exception as error:

        print(
            "GET STORY ERROR:",
            error
        )

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


# =====================================================
# UPDATE LIVING STORY
# =====================================================

@app.post(
    "/stories/{story_id}/update",
    response_model=LivingStory
)
def update_living_story(
    story_id: str,
    request: StoryUpdateRequest
):

    try:

        if not request.article.strip():

            raise HTTPException(
                status_code=400,
                detail="New article cannot be empty"
            )


        result = update_story(
            story_id=story_id,
            article=request.article,
            source_name=request.source_name
        )


        if not result:

            raise HTTPException(
                status_code=404,
                detail="Story not found"
            )


        return result


    except HTTPException:
        raise


    except Exception as error:

        print(
            "UPDATE STORY ERROR:",
            error
        )

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


# =====================================================
# SCOUT AGENT / LATEST NEWS
# =====================================================

@app.get(
    "/news/latest",
    response_model=NewsCollectionResponse
)
def get_latest_news(
    limit: int = Query(
        default=3,
        ge=1,
        le=20
    )
):

    try:

        articles = collect_latest_news(
            limit_per_source=limit
        )


        return NewsCollectionResponse(
            total_articles=len(
                articles
            ),
            articles=articles
        )


    except Exception as error:

        print(
            "NEWS COLLECTOR ERROR:",
            error
        )

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


# =====================================================
# STORY CLUSTERING
# =====================================================

@app.get(
    "/news/clusters",
    response_model=StoryClusteringResponse
)
def get_story_clusters(
    limit: int = Query(
        default=3,
        ge=1,
        le=20
    ),

    similarity: float = Query(
        default=0.50,
        ge=0.40,
        le=0.95
    )
):

    try:

        articles = collect_latest_news(
            limit_per_source=limit
        )


        return cluster_articles(
            articles=articles,
            similarity_threshold=similarity
        )


    except Exception as error:

        print(
            "STORY CLUSTER ERROR:",
            error
        )

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )