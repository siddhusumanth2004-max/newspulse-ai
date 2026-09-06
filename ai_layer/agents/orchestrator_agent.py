import time

from typing import List

from models.schemas import (
    CollectedArticle,
    DeltaResponse,
    OrchestratedStory,
    OrchestratorResponse,
)

from services.news_collector import (
    collect_latest_news,
)

from services.story_cluster import (
    cluster_articles
    as cluster_news_articles,
)

from services.story_matcher import (
    find_matching_story,
)

from services.story_memory import (
    create_story_with_analysis,
    update_story_with_analysis,
)

from agents.news_intelligence_agent import (
    analyze_news_story,
)


# =========================================================
# NEWSPULSE ROLE-BASED FAST ORCHESTRATOR
# =========================================================


# =========================================================
# BUILD STORY CONTEXT
#
# We intentionally send only the first 3 articles
# and shorten very large RSS summaries.
#
# This reduces Claude input tokens and latency.
# =========================================================

def build_story_context(
    articles: List[
        CollectedArticle
    ],
) -> str:

    sections = []

    for index, article in enumerate(
        articles[:3],
        start=1,
    ):

        summary = (
            article.summary
            or ""
        )

        if len(summary) > 900:

            summary = (
                summary[:900]
                + "..."
            )


        section = f"""
SOURCE {index}

Publisher:
{article.source}

Headline:
{article.title}

Summary:
{summary}

Published:
{article.published}

Original Link:
{article.link}
"""

        sections.append(
            section.strip()
        )


    return "\n\n".join(
        sections
    )


# =========================================================
# BUILD STORY MATCHING TEXT
#
# Keep memory matching compact as well.
# =========================================================

def build_matching_text(
    representative_title: str,
    articles: List[
        CollectedArticle
    ],
) -> str:

    pieces = [
        representative_title
    ]


    for article in articles[:3]:

        summary = (
            article.summary
            or ""
        )

        pieces.append(
            (
                f"{article.title}. "
                f"{summary[:350]}"
            )
        )


    return " ".join(
        pieces
    )


# =========================================================
# MAIN ORCHESTRATOR
# =========================================================

def run_orchestrator(
    user_role: str,
    limit_per_source: int,
    similarity_threshold: float,
    max_stories: int,
) -> OrchestratorResponse:

    total_started = (
        time.perf_counter()
    )


    selected_role = (
        user_role
        or "General Reader"
    ).strip()


    print()
    print(
        "========================================"
    )
    print(
        "NEWSPULSE ROLE-BASED FAST LANGCHAIN"
    )
    print(
        "ROLE:",
        selected_role
    )
    print(
        "========================================"
    )


    # =====================================================
    # STEP 1
    # COLLECT ONLY ROLE-RELEVANT NEWS
    # =====================================================

    collection_started = (
        time.perf_counter()
    )


    print()
    print(
        "[1] COLLECTING ROLE-BASED LIVE NEWS"
    )


    articles = collect_latest_news(

        limit_per_source=
            limit_per_source,

        user_role=
            selected_role,
    )


    collection_time = (
        time.perf_counter()
        - collection_started
    )


    print(
        "[TIMING] News collection:",
        f"{collection_time:.2f}s"
    )


    # =====================================================
    # NO ARTICLES
    # =====================================================

    if not articles:

        return OrchestratorResponse(

            agent_name=(
                "NewsPulse Role-Based Fast "
                "LangChain Intelligence Agent"
            ),

            total_articles_collected=0,

            total_story_clusters=0,

            analyzed_stories=0,

            new_stories_created=0,

            existing_stories_updated=0,

            user_role=selected_role,

            stories=[],
        )


    print(
        "Articles collected:",
        len(articles)
    )


    # =====================================================
    # STEP 2
    # CLUSTER SIMILAR NEWS
    # =====================================================

    clustering_started = (
        time.perf_counter()
    )


    print()
    print(
        "[2] CLUSTERING NEWS"
    )


    clustering_result = (
        cluster_news_articles(

            articles=articles,

            similarity_threshold=
                similarity_threshold,
        )
    )


    clustering_time = (
        time.perf_counter()
        - clustering_started
    )


    print(
        "[TIMING] Clustering:",
        f"{clustering_time:.2f}s"
    )


    sorted_clusters = sorted(

        clustering_result.clusters,

        key=lambda cluster:
            cluster.article_count,

        reverse=True,
    )


    selected_clusters = (
        sorted_clusters[
            :max_stories
        ]
    )


    print(
        "Total clusters:",
        clustering_result.total_clusters
    )

    print(
        "Stories selected:",
        len(selected_clusters)
    )


    # =====================================================
    # COUNTERS
    # =====================================================

    analyzed_results = []

    new_story_count = 0

    updated_story_count = 0

    used_story_ids = set()


    # =====================================================
    # STEP 3+
    # PROCESS SELECTED STORIES
    #
    # Claude remains sequential in this version.
    #
    # We keep it this way for stability.
    # Collection speed + smaller Claude context
    # already reduce response time.
    # =====================================================

    for index, cluster in enumerate(
        selected_clusters,
        start=1,
    ):

        story_started = (
            time.perf_counter()
        )


        print()
        print(
            "========================================"
        )

        print(
            f"PROCESSING STORY {index}"
        )

        print(
            cluster.representative_title
        )

        print(
            "========================================"
        )


        story_articles = (
            cluster.articles
        )


        # =================================================
        # BUILD COMPACT LLM CONTEXT
        # =================================================

        story_context = (
            build_story_context(
                story_articles
            )
        )


        # =================================================
        # CHECK LIVING STORY MEMORY
        # =================================================

        print()
        print(
            "[3] CHECKING LIVING STORY MEMORY"
        )


        matching_text = (
            build_matching_text(

                representative_title=
                    cluster
                    .representative_title,

                articles=
                    story_articles,
            )
        )


        (
            matched_story,
            similarity_score,
        ) = find_matching_story(

            new_story_text=
                matching_text,

            threshold=0.58,

            excluded_story_ids=
                used_story_ids,
        )


        previous_story = None


        if matched_story:

            previous_story = (
                matched_story
                .latest_article
            )

            print(
                "Existing Living Story matched."
            )

            print(
                "Story ID:",
                matched_story.story_id
            )

            print(
                "Similarity:",
                round(
                    float(
                        similarity_score
                    ),
                    4,
                )
            )


        else:

            print(
                "No previous story matched."
            )

            print(
                "Creating a new Living Story."
            )


        # =================================================
        # RUN WORKING LANGCHAIN / CLAUDE AGENT
        #
        # IMPORTANT:
        # We do NOT change news_intelligence_agent.py.
        # =================================================

        print()
        print(
            "[4] RUNNING LANGCHAIN AGENT"
        )


        ai_started = (
            time.perf_counter()
        )


        analysis = (
            analyze_news_story(

                story_context=
                    story_context,

                user_role=
                    selected_role,

                source_count=
                    cluster.article_count,

                previous_story=
                    previous_story,
            )
        )


        print(
            "[TIMING] Claude:",
            f"{time.perf_counter() - ai_started:.2f}s"
        )


        # =================================================
        # SAVE / UPDATE LIVING STORY
        # =================================================

        print()
        print(
            "[5] UPDATING STORY MEMORY"
        )


        if matched_story:

            delta = (
                analysis.delta
            )


            # =============================================
            # DELTA FALLBACK
            # =============================================

            if delta is None:

                delta = DeltaResponse(

                    what_changed=(
                        "No clear material "
                        "change was identified."
                    ),

                    new_information=[],

                    confirmed_information=[],

                    changed_information=[],

                    corrected_information=[],

                    still_uncertain=[],
                )


            saved_story = (
                update_story_with_analysis(

                    story_id=
                        matched_story
                        .story_id,

                    article=
                        story_context,

                    source_name=
                        "NewsPulse LangChain",

                    briefing=
                        analysis.briefing,

                    delta=
                        delta,
                )
            )


            # =============================================
            # IF UPDATE FAILED
            # CREATE NEW STORY SAFELY
            # =============================================

            if saved_story is None:

                saved_story = (
                    create_story_with_analysis(

                        title=
                            analysis
                            .briefing
                            .headline,

                        article=
                            story_context,

                        source_name=
                            "NewsPulse LangChain",

                        briefing=
                            analysis.briefing,
                    )
                )


                memory_action = (
                    "CREATED"
                )

                new_story_count += 1


            else:

                memory_action = (
                    "UPDATED"
                )

                updated_story_count += 1


        else:

            delta = None


            saved_story = (
                create_story_with_analysis(

                    title=
                        analysis
                        .briefing
                        .headline,

                    article=
                        story_context,

                    source_name=
                        "NewsPulse LangChain",

                    briefing=
                        analysis.briefing,
                )
            )


            memory_action = (
                "CREATED"
            )

            new_story_count += 1


        # =================================================
        # PREVENT SAME MEMORY MATCH TWICE
        # =================================================

        used_story_ids.add(
            saved_story.story_id
        )


        # =================================================
        # EVIDENCE MESSAGE
        # =================================================

        if (
            cluster.article_count >= 2
            and
            analysis.evidence is not None
        ):

            evidence_note = (
                "Multi-source evidence analysis "
                "completed by the NewsPulse "
                "LangChain agent."
            )


        elif cluster.article_count < 2:

            evidence_note = (
                "Only one source was available. "
                "Independent multi-source "
                "verification was not possible."
            )


        else:

            evidence_note = (
                "The available sources were "
                "not sufficient for a reliable "
                "evidence conclusion."
            )


        # =================================================
        # FRONTEND RESPONSE
        # =================================================

        orchestrated_story = (
            OrchestratedStory(

                cluster_id=
                    cluster.cluster_id,

                representative_title=
                    cluster
                    .representative_title,

                article_count=
                    cluster.article_count,

                briefing=
                    analysis.briefing,

                evidence=
                    analysis.evidence,

                evidence_note=
                    evidence_note,

                impact=
                    analysis.impact,

                living_story_id=
                    saved_story.story_id,

                memory_action=
                    memory_action,

                memory_similarity=
                    round(
                        float(
                            similarity_score
                        ),
                        4,
                    ),

                delta=
                    delta,

                sources=
                    story_articles,
            )
        )


        analyzed_results.append(
            orchestrated_story
        )


        print(
            "Story completed in:",
            f"{time.perf_counter() - story_started:.2f}s"
        )

        print(
            "Memory action:",
            memory_action
        )


    # =====================================================
    # FINAL RESPONSE
    # =====================================================

    response = (
        OrchestratorResponse(

            agent_name=(
                "NewsPulse Role-Based Fast "
                "LangChain Intelligence Agent"
            ),

            total_articles_collected=
                len(articles),

            total_story_clusters=
                clustering_result
                .total_clusters,

            analyzed_stories=
                len(
                    analyzed_results
                ),

            new_stories_created=
                new_story_count,

            existing_stories_updated=
                updated_story_count,

            user_role=
                selected_role,

            stories=
                analyzed_results,
        )
    )


    total_time = (
        time.perf_counter()
        - total_started
    )


    print()
    print(
        "========================================"
    )

    print(
        "NEWSPULSE COMPLETE"
    )

    print(
        "Role:",
        selected_role
    )

    print(
        "Articles:",
        response.total_articles_collected
    )

    print(
        "Clusters:",
        response.total_story_clusters
    )

    print(
        "Analyzed:",
        response.analyzed_stories
    )

    print(
        "Total time:",
        f"{total_time:.2f}s"
    )

    print(
        "========================================"
    )


    return response