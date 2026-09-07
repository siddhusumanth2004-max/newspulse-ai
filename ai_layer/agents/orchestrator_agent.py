import copy
import hashlib
import threading
import time

from concurrent.futures import (
    ThreadPoolExecutor,
    as_completed,
)

from typing import (
    Dict,
    List,
    Tuple,
)

from models.schemas import (
    CollectedArticle,
    DeltaResponse,
    OrchestratedStory,
    OrchestratorResponse,
    SingleAgentAnalysis,
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
# NEWSPULSE FAST ORCHESTRATOR
# =========================================================


# =========================================================
# PERFORMANCE SETTINGS
#
# Keep this at 2.
#
# Two Claude requests can run together.
# Increasing it too much may cause rate limits.
# =========================================================

MAX_PARALLEL_AI_CALLS = 2


# Number of articles from one cluster
# that are sent to Claude.
MAX_CONTEXT_SOURCES = 3


# Maximum summary characters for each source.
MAX_SUMMARY_CHARS = 650


# AI analysis cache lifetime.
AI_CACHE_TTL_SECONDS = 300


# Maximum number of cached AI analyses.
MAX_AI_CACHE_ITEMS = 100


# =========================================================
# AI CACHE
#
# key ->
# (
#     timestamp,
#     SingleAgentAnalysis
# )
# =========================================================

_ai_cache: Dict[
    str,
    Tuple[
        float,
        SingleAgentAnalysis,
    ],
] = {}


_ai_cache_lock = threading.Lock()


# =========================================================
# BUILD STORY CONTEXT
#
# Smaller context = fewer Claude input tokens.
# =========================================================

def build_story_context(
    articles: List[CollectedArticle],
) -> str:

    sections = []

    for index, article in enumerate(
        articles[:MAX_CONTEXT_SOURCES],
        start=1,
    ):

        summary = (
            article.summary
            or ""
        ).strip()

        if len(summary) > MAX_SUMMARY_CHARS:

            summary = (
                summary[
                    :MAX_SUMMARY_CHARS
                ]
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
""".strip()


        sections.append(
            section
        )


    return "\n\n".join(
        sections
    )


# =========================================================
# BUILD STORY MATCHING TEXT
#
# Used only for SentenceTransformer memory matching.
# =========================================================

def build_matching_text(
    representative_title: str,
    articles: List[CollectedArticle],
) -> str:

    pieces = [
        representative_title
    ]


    for article in articles[
        :MAX_CONTEXT_SOURCES
    ]:

        summary = (
            article.summary
            or ""
        ).strip()

        pieces.append(
            (
                f"{article.title}. "
                f"{summary[:300]}"
            )
        )


    return " ".join(
        pieces
    )


# =========================================================
# AI CACHE KEY
#
# previous_story is included because Delta / What Changed
# depends on the previous Living Story.
# =========================================================

def build_ai_cache_key(
    story_context: str,
    user_role: str,
    source_count: int,
    previous_story: str | None,
) -> str:

    raw_key = (
        f"ROLE={user_role}\n"
        f"SOURCES={source_count}\n"
        f"CURRENT={story_context}\n"
        f"PREVIOUS={previous_story or ''}"
    )


    return hashlib.sha256(
        raw_key.encode(
            "utf-8"
        )
    ).hexdigest()


# =========================================================
# AI CACHE READ
# =========================================================

def get_cached_analysis(
    cache_key: str,
):

    with _ai_cache_lock:

        cached = _ai_cache.get(
            cache_key
        )

        if cached is None:

            return None


        cached_time, analysis = cached


        cache_age = (
            time.time()
            - cached_time
        )


        if cache_age > AI_CACHE_TTL_SECONDS:

            _ai_cache.pop(
                cache_key,
                None,
            )

            return None


        # Return a deep copy because later code may modify
        # delta/evidence values.
        return copy.deepcopy(
            analysis
        )


# =========================================================
# AI CACHE WRITE
# =========================================================

def save_cached_analysis(
    cache_key: str,
    analysis: SingleAgentAnalysis,
):

    with _ai_cache_lock:

        # Keep cache small.
        if (
            len(_ai_cache)
            >= MAX_AI_CACHE_ITEMS
        ):

            oldest_key = min(
                _ai_cache,

                key=lambda key:
                    _ai_cache[
                        key
                    ][0],
            )

            _ai_cache.pop(
                oldest_key,
                None,
            )


        _ai_cache[
            cache_key
        ] = (
            time.time(),
            copy.deepcopy(
                analysis
            ),
        )


# =========================================================
# ANALYZE ONE STORY
#
# This function runs inside ThreadPoolExecutor.
# =========================================================

def analyze_prepared_story(
    prepared_item: dict,
    user_role: str,
) -> SingleAgentAnalysis:

    story_number = (
        prepared_item[
            "story_number"
        ]
    )

    story_context = (
        prepared_item[
            "story_context"
        ]
    )

    previous_story = (
        prepared_item[
            "previous_story"
        ]
    )

    source_count = (
        prepared_item[
            "cluster"
        ].article_count
    )


    cache_key = build_ai_cache_key(
        story_context=story_context,

        user_role=user_role,

        source_count=source_count,

        previous_story=previous_story,
    )


    # =====================================================
    # CACHE CHECK
    # =====================================================

    cached_analysis = (
        get_cached_analysis(
            cache_key
        )
    )


    if cached_analysis is not None:

        print(
            f"[AI CACHE HIT] "
            f"Story {story_number}"
        )

        return cached_analysis


    # =====================================================
    # CLAUDE CALL
    # =====================================================

    print(
        f"[AI START] "
        f"Story {story_number}"
    )


    ai_started = (
        time.perf_counter()
    )


    analysis = (
        analyze_news_story(

            story_context=
                story_context,

            user_role=
                user_role,

            source_count=
                source_count,

            previous_story=
                previous_story,
        )
    )


    ai_time = (
        time.perf_counter()
        - ai_started
    )


    print(
        f"[AI COMPLETE] "
        f"Story {story_number}: "
        f"{ai_time:.2f}s"
    )


    # =====================================================
    # CACHE SUCCESSFUL RESULT
    # =====================================================

    save_cached_analysis(
        cache_key,
        analysis,
    )


    return analysis


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


    max_stories = max(
        1,
        int(max_stories),
    )


    print()
    print(
        "========================================"
    )

    print(
        "NEWSPULSE HIGH-SPEED LANGCHAIN AGENT"
    )

    print(
        "ROLE:",
        selected_role
    )

    print(
        "PARALLEL AI CALLS:",
        MAX_PARALLEL_AI_CALLS
    )

    print(
        "========================================"
    )


    # =====================================================
    # STEP 1
    # ROLE-BASED NEWS COLLECTION
    # =====================================================

    collection_started = (
        time.perf_counter()
    )


    print()
    print(
        "[1] COLLECTING ROLE-BASED NEWS"
    )


    articles = (
        collect_latest_news(

            limit_per_source=
                limit_per_source,

            user_role=
                selected_role,
        )
    )


    collection_time = (
        time.perf_counter()
        - collection_started
    )


    print(
        "[TIMING] Collection:",
        f"{collection_time:.2f}s"
    )


    # =====================================================
    # NO NEWS
    # =====================================================

    if not articles:

        return OrchestratorResponse(

            agent_name=(
                "NewsPulse High-Speed "
                "LangChain Intelligence Agent"
            ),

            total_articles_collected=0,

            total_story_clusters=0,

            analyzed_stories=0,

            new_stories_created=0,

            existing_stories_updated=0,

            user_role=
                selected_role,

            stories=[],
        )


    # =====================================================
    # STEP 2
    # STORY CLUSTERING
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


    # =====================================================
    # PICK MOST IMPORTANT CLUSTERS
    # =====================================================

    selected_clusters = sorted(

        clustering_result.clusters,

        key=lambda cluster:
            cluster.article_count,

        reverse=True,

    )[:max_stories]


    print(
        "Articles:",
        len(articles)
    )

    print(
        "Clusters:",
        clustering_result.total_clusters
    )

    print(
        "Stories selected:",
        len(selected_clusters)
    )


    # =====================================================
    # STEP 3
    # LIVING STORY MATCHING
    #
    # Do this sequentially.
    #
    # This prevents the same saved story from
    # matching multiple new clusters.
    # =====================================================

    matching_started = (
        time.perf_counter()
    )


    print()
    print(
        "[3] MATCHING LIVING STORIES"
    )


    prepared_stories = []

    used_story_ids = set()


    for story_number, cluster in enumerate(
        selected_clusters,
        start=1,
    ):

        story_articles = (
            cluster.articles
        )


        story_context = (
            build_story_context(
                story_articles
            )
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


            used_story_ids.add(
                matched_story.story_id
            )


            print(
                f"Story {story_number}: "
                f"MATCHED "
                f"({similarity_score:.4f})"
            )


        else:

            print(
                f"Story {story_number}: "
                "NEW STORY"
            )


        prepared_stories.append(
            {
                "story_number":
                    story_number,

                "cluster":
                    cluster,

                "story_articles":
                    story_articles,

                "story_context":
                    story_context,

                "matched_story":
                    matched_story,

                "similarity_score":
                    similarity_score,

                "previous_story":
                    previous_story,
            }
        )


    matching_time = (
        time.perf_counter()
        - matching_started
    )


    print(
        "[TIMING] Memory matching:",
        f"{matching_time:.2f}s"
    )


    # =====================================================
    # STEP 4
    # PARALLEL CLAUDE ANALYSIS
    #
    # Old:
    #
    # Story 1 -> wait
    # Story 2 -> wait
    # Story 3 -> wait
    #
    # New:
    #
    # Story 1 ─┐
    #           ├── Claude together
    # Story 2 ─┘
    #
    # Max 2 at once.
    # =====================================================

    ai_started = (
        time.perf_counter()
    )


    print()
    print(
        "[4] RUNNING LANGCHAIN + CLAUDE"
    )


    analyses = {}


    worker_count = min(
        MAX_PARALLEL_AI_CALLS,
        len(prepared_stories),
    )


    failed_items = []


    if worker_count > 0:

        with ThreadPoolExecutor(
            max_workers=worker_count
        ) as executor:

            future_map = {}


            for item in prepared_stories:

                future = executor.submit(
                    analyze_prepared_story,

                    item,

                    selected_role,
                )


                future_map[
                    future
                ] = item


            for future in as_completed(
                future_map
            ):

                item = (
                    future_map[
                        future
                    ]
                )


                story_number = (
                    item[
                        "story_number"
                    ]
                )


                try:

                    analyses[
                        story_number
                    ] = (
                        future.result()
                    )


                except Exception as error:

                    print(
                        f"[AI PARALLEL ERROR] "
                        f"Story {story_number}: "
                        f"{error}"
                    )


                    # Retry sequentially later.
                    failed_items.append(
                        item
                    )


    # =====================================================
    # SAFETY RETRY
    #
    # If one parallel request fails due to a temporary
    # API/network/rate-limit issue, retry only that story.
    # =====================================================

    for item in failed_items:

        story_number = (
            item[
                "story_number"
            ]
        )


        print(
            f"[AI RETRY] "
            f"Story {story_number} "
            f"sequential retry..."
        )


        analyses[
            story_number
        ] = (
            analyze_prepared_story(

                item,

                selected_role,
            )
        )


    ai_time = (
        time.perf_counter()
        - ai_started
    )


    print(
        "[TIMING] Total AI stage:",
        f"{ai_time:.2f}s"
    )


    # =====================================================
    # STEP 5
    # SAVE LIVING STORIES
    #
    # IMPORTANT:
    #
    # AI generation is parallel.
    #
    # File/story-memory writing remains sequential
    # to avoid corrupting the memory store.
    # =====================================================

    save_started = (
        time.perf_counter()
    )


    print()
    print(
        "[5] SAVING LIVING STORY MEMORY"
    )


    orchestrated_results = []

    new_story_count = 0

    updated_story_count = 0


    for item in prepared_stories:

        story_number = (
            item[
                "story_number"
            ]
        )


        cluster = (
            item[
                "cluster"
            ]
        )


        story_articles = (
            item[
                "story_articles"
            ]
        )


        story_context = (
            item[
                "story_context"
            ]
        )


        matched_story = (
            item[
                "matched_story"
            ]
        )


        similarity_score = (
            item[
                "similarity_score"
            ]
        )


        analysis = (
            analyses[
                story_number
            ]
        )


        # =================================================
        # EXISTING STORY
        # =================================================

        if matched_story:

            delta = (
                analysis.delta
            )


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
            # UPDATE FAILED
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


        # =================================================
        # NEW STORY
        # =================================================

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
        # EVIDENCE NOTE
        # =================================================

        if (
            cluster.article_count >= 2
            and
            analysis.evidence is not None
        ):

            evidence_note = (
                "Multi-source evidence "
                "analysis completed by "
                "NewsPulse."
            )


        elif cluster.article_count < 2:

            evidence_note = (
                "Only one source was available. "
                "Independent multi-source "
                "verification was not possible."
            )


        else:

            evidence_note = (
                "Available sources were "
                "insufficient for reliable "
                "multi-source evidence analysis."
            )


        # =================================================
        # RESPONSE STORY
        # =================================================

        orchestrated_results.append(
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


    save_time = (
        time.perf_counter()
        - save_started
    )


    print(
        "[TIMING] Memory save:",
        f"{save_time:.2f}s"
    )


    # =====================================================
    # FINAL RESPONSE
    # =====================================================

    total_time = (
        time.perf_counter()
        - total_started
    )


    response = (
        OrchestratorResponse(

            agent_name=(
                "NewsPulse High-Speed "
                "Role-Based LangChain "
                "Intelligence Agent"
            ),

            total_articles_collected=
                len(articles),

            total_story_clusters=
                clustering_result
                .total_clusters,

            analyzed_stories=
                len(
                    orchestrated_results
                ),

            new_stories_created=
                new_story_count,

            existing_stories_updated=
                updated_story_count,

            user_role=
                selected_role,

            stories=
                orchestrated_results,
        )
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
        len(articles)
    )

    print(
        "Stories analyzed:",
        len(
            orchestrated_results
        )
    )

    print(
        "Collection:",
        f"{collection_time:.2f}s"
    )

    print(
        "Clustering:",
        f"{clustering_time:.2f}s"
    )

    print(
        "Matching:",
        f"{matching_time:.2f}s"
    )

    print(
        "AI:",
        f"{ai_time:.2f}s"
    )

    print(
        "Memory save:",
        f"{save_time:.2f}s"
    )

    print(
        "TOTAL:",
        f"{total_time:.2f}s"
    )

    print(
        "========================================"
    )


    return response