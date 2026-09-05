from typing import List

from models.schemas import (
    CollectedArticle,
    DeltaResponse,
    OrchestratedStory,
    OrchestratorResponse
)

from services.news_collector import (
    collect_latest_news
)

from services.story_cluster import (
    cluster_articles
    as cluster_news_articles
)

from services.story_matcher import (
    find_matching_story
)

from services.story_memory import (
    create_story_with_analysis,
    update_story_with_analysis
)

from agents.news_intelligence_agent import (
    analyze_news_story
)


# =====================================================
# BUILD STORY CONTEXT
# =====================================================

def build_story_context(
    articles: List[
        CollectedArticle
    ]
) -> str:

    sections = []


    for index, article in enumerate(
        articles,
        start=1
    ):

        section = f"""
SOURCE {index}

Publisher:
{article.source}

Headline:
{article.title}

Summary:
{article.summary}

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


# =====================================================
# BUILD MEMORY MATCHING TEXT
# =====================================================

def build_matching_text(
    representative_title: str,
    articles: List[
        CollectedArticle
    ]
) -> str:

    titles = " ".join(

        article.title

        for article
        in articles

    )


    summaries = " ".join(

        article.summary

        for article
        in articles

    )


    return (

        f"{representative_title}. "

        f"{titles}. "

        f"{summaries}"

    )


# =====================================================
# NEWSPULSE LANGCHAIN ORCHESTRATOR
# =====================================================

def run_orchestrator(
    user_role: str,
    limit_per_source: int,
    similarity_threshold: float,
    max_stories: int
) -> OrchestratorResponse:

    print()

    print(
        "========================================"
    )

    print(
        "NEWSPULSE LANGCHAIN"
    )

    print(
        "SINGLE-AGENT ORCHESTRATOR"
    )

    print(
        "========================================"
    )


    # =================================================
    # STEP 1
    # COLLECT LIVE NEWS
    # =================================================

    print()

    print(
        "[1] COLLECTING LIVE NEWS"
    )


    articles = collect_latest_news(

        limit_per_source=
            limit_per_source

    )


    print(
        "Articles collected:",
        len(articles)
    )


    # =================================================
    # NO ARTICLES
    # =================================================

    if not articles:

        return OrchestratorResponse(

            agent_name=(
                "NewsPulse Single-Agent "
                "LangChain Intelligence"
            ),

            total_articles_collected=0,

            total_story_clusters=0,

            analyzed_stories=0,

            new_stories_created=0,

            existing_stories_updated=0,

            user_role=user_role,

            stories=[]
        )


    # =================================================
    # STEP 2
    # CLUSTER SIMILAR NEWS
    # =================================================

    print()

    print(
        "[2] CLUSTERING NEWS"
    )


    clustering_result = (
        cluster_news_articles(

            articles=articles,

            similarity_threshold=
                similarity_threshold

        )
    )


    sorted_clusters = sorted(

        clustering_result.clusters,

        key=lambda cluster:
            cluster.article_count,

        reverse=True

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


    # =================================================
    # COUNTERS
    # =================================================

    analyzed_results = []

    new_story_count = 0

    updated_story_count = 0

    used_story_ids = set()


    # =================================================
    # STEP 3
    # PROCESS EVERY SELECTED STORY
    # =================================================

    for index, cluster in enumerate(
        selected_clusters,
        start=1
    ):

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


        story_context = (
            build_story_context(
                story_articles
            )
        )


        # =============================================
        # STEP 3A
        # CHECK LIVING STORY MEMORY
        # =============================================

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
                    story_articles

            )
        )


        (
            matched_story,
            similarity_score
        ) = find_matching_story(

            new_story_text=
                matching_text,

            threshold=0.58,

            excluded_story_ids=
                used_story_ids

        )


        previous_story = None


        if matched_story:

            previous_story = (
                matched_story
                .latest_article
            )


            print(
                "Existing story matched."
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
                    4
                )
            )


        else:

            print(
                "No previous story matched."
            )

            print(
                "This will be a new "
                "Living Story."
            )


        # =============================================
        # STEP 4
        # RUN SINGLE LANGCHAIN AI AGENT
        # =============================================

        print()

        print(
            "[4] RUNNING LANGCHAIN AGENT"
        )


        analysis = analyze_news_story(

            story_context=
                story_context,

            user_role=
                user_role,

            source_count=
                cluster.article_count,

            previous_story=
                previous_story

        )


        # =============================================
        # STEP 5
        # SAVE / UPDATE LIVING STORY
        # =============================================

        print()

        print(
            "[5] UPDATING STORY MEMORY"
        )


        if matched_story:

            delta = (
                analysis.delta
            )


            # =========================================
            # FALLBACK
            # =========================================

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

                    still_uncertain=[]

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
                        delta

                )
            )


            # =========================================
            # IF UPDATE FAILED
            # CREATE NEW STORY
            # =========================================

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
                            analysis.briefing

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
                        analysis.briefing

                )
            )


            memory_action = (
                "CREATED"
            )


            new_story_count += 1


        # =============================================
        # PREVENT SAME MEMORY FROM BEING USED TWICE
        # =============================================

        used_story_ids.add(
            saved_story.story_id
        )


        # =============================================
        # STEP 6
        # EVIDENCE MESSAGE
        # =============================================

        if (
            cluster.article_count >= 2
            and
            analysis.evidence is not None
        ):

            evidence_note = (
                "Multi-source evidence "
                "analysis completed by the "
                "NewsPulse LangChain agent."
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


        # =============================================
        # STEP 7
        # BUILD FRONTEND RESPONSE
        # =============================================

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
                        4
                    ),

                delta=
                    delta,

                sources=
                    story_articles

            )
        )


        analyzed_results.append(
            orchestrated_story
        )


        print()

        print(
            "Story completed."
        )

        print(
            "Memory action:",
            memory_action
        )


    # =================================================
    # STEP 8
    # FINAL RESPONSE
    # =================================================

    response = (
        OrchestratorResponse(

            agent_name=(
                "NewsPulse Single-Agent "
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
                user_role,

            stories=
                analyzed_results

        )
    )


    print()

    print(
        "========================================"
    )

    print(
        "NEWSPULSE LANGCHAIN COMPLETE"
    )

    print(
        "========================================"
    )


    print(
        "Articles:",
        response
        .total_articles_collected
    )


    print(
        "Clusters:",
        response
        .total_story_clusters
    )


    print(
        "Analyzed:",
        response
        .analyzed_stories
    )


    print(
        "New stories:",
        response
        .new_stories_created
    )


    print(
        "Updated stories:",
        response
        .existing_stories_updated
    )


    print(
        "========================================"
    )


    return response