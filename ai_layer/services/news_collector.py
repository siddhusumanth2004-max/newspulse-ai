import html
import re
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

from urllib.parse import quote_plus

import feedparser
import requests

from models.schemas import CollectedArticle


# =========================================================
# NEWSPULSE ROLE-BASED FAST NEWS COLLECTOR
# =========================================================


# =========================================================
# PERFORMANCE SETTINGS
# =========================================================

REQUEST_TIMEOUT_SECONDS = 4

CACHE_TTL_SECONDS = 300

MAX_PARALLEL_FEEDS = 3

MAX_ARTICLES_TO_SCAN_PER_FEED = 20


# =========================================================
# ROLE CONFIGURATION
#
# Each role receives its own Google News searches.
# =========================================================

ROLE_CONFIG = {

    "Student": {

        "queries": [
            (
                "Education News",
                (
                    "students education university college "
                    "exams admissions scholarships India"
                ),
            ),
            (
                "Student Opportunities",
                (
                    "students internships campus placements "
                    "jobs careers skills India"
                ),
            ),
        ],

        "keywords": [
            "student",
            "students",
            "education",
            "college",
            "colleges",
            "university",
            "universities",
            "school",
            "schools",
            "exam",
            "exams",
            "examination",
            "admission",
            "admissions",
            "scholarship",
            "scholarships",
            "internship",
            "internships",
            "campus",
            "placement",
            "placements",
            "career",
            "careers",
            "course",
            "courses",
            "degree",
            "graduate",
            "graduates",
            "learning",
            "skills",
            "jee",
            "neet",
            "gate",
            "upsc",
            "mbbs",
        ],
    },

    "Developer": {

        "queries": [
            (
                "Developer News",
                (
                    "software developers programming "
                    "AI developer tools APIs"
                ),
            ),
            (
                "Software Technology",
                (
                    "software engineering cloud cybersecurity "
                    "programming frameworks developers"
                ),
            ),
        ],

        "keywords": [
            "developer",
            "developers",
            "programming",
            "software",
            "coding",
            "code",
            "api",
            "apis",
            "framework",
            "frameworks",
            "python",
            "javascript",
            "java",
            "react",
            "node",
            "cloud",
            "cybersecurity",
            "security",
            "github",
            "open source",
            "artificial intelligence",
            "ai tool",
            "ai tools",
            "machine learning",
            "database",
        ],
    },

    "Researcher": {

        "queries": [
            (
                "Scientific Research",
                (
                    "scientific research researchers "
                    "university study discovery"
                ),
            ),
            (
                "Academic Research",
                (
                    "academic research science "
                    "research paper AI research"
                ),
            ),
        ],

        "keywords": [
            "research",
            "researcher",
            "researchers",
            "study",
            "studies",
            "science",
            "scientific",
            "discovery",
            "discoveries",
            "paper",
            "papers",
            "academic",
            "university",
            "laboratory",
            "lab",
            "experiment",
            "experiments",
            "journal",
            "findings",
            "dataset",
        ],
    },

    "Business Owner": {

        "queries": [
            (
                "Business News",
                (
                    "business startups entrepreneurship "
                    "companies markets India"
                ),
            ),
            (
                "Business Technology",
                (
                    "business technology AI companies "
                    "SME regulation India"
                ),
            ),
        ],

        "keywords": [
            "business",
            "businesses",
            "company",
            "companies",
            "startup",
            "startups",
            "entrepreneur",
            "entrepreneurship",
            "market",
            "markets",
            "industry",
            "industries",
            "revenue",
            "sales",
            "customer",
            "customers",
            "regulation",
            "regulations",
            "economy",
            "economic",
            "investment",
            "investments",
            "sme",
            "enterprise",
        ],
    },

    "General Reader": {

        "queries": [
            (
                "India News",
                "India latest news",
            ),
            (
                "World News",
                "world latest news",
            ),
            (
                "Technology News",
                "technology latest news",
            ),
        ],

        "keywords": [],
    },
}


# =========================================================
# IN-MEMORY RSS CACHE
#
# feed_url ->
# (
#     timestamp,
#     List[CollectedArticle]
# )
# =========================================================

_feed_cache: Dict[
    str,
    Tuple[
        float,
        List[CollectedArticle],
    ],
] = {}


_cache_lock = threading.Lock()


# =========================================================
# TEXT CLEANING
# =========================================================

def clean_text(
    value: str,
) -> str:

    if not value:
        return ""

    value = html.unescape(
        str(value)
    )

    value = re.sub(
        r"<[^>]+>",
        " ",
        value,
    )

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value.strip()


# =========================================================
# NORMALIZE ROLE
# =========================================================

def normalize_role(
    user_role: str,
) -> str:

    selected_role = (
        user_role
        or "General Reader"
    ).strip()

    if selected_role in ROLE_CONFIG:
        return selected_role

    return "General Reader"


# =========================================================
# GOOGLE NEWS RSS SEARCH URL
# =========================================================

def build_google_news_url(
    query: str,
) -> str:

    encoded_query = quote_plus(
        query
    )

    return (
        "https://news.google.com/rss/search"
        f"?q={encoded_query}"
        "&hl=en-IN"
        "&gl=IN"
        "&ceid=IN:en"
    )


# =========================================================
# ROLE FEEDS
# =========================================================

def get_feeds_for_role(
    user_role: str,
):

    selected_role = normalize_role(
        user_role
    )

    queries = ROLE_CONFIG[
        selected_role
    ]["queries"]

    feeds = []

    for source_name, query in queries:

        feeds.append(
            {
                "name": source_name,

                "url": (
                    build_google_news_url(
                        query
                    )
                ),
            }
        )

    return feeds


# =========================================================
# ARTICLE HELPERS
# =========================================================

def get_title(
    entry,
) -> str:

    return clean_text(
        entry.get(
            "title",
            "",
        )
    )


def get_summary(
    entry,
) -> str:

    return clean_text(
        entry.get("summary")
        or entry.get("description")
        or ""
    )


def get_published(
    entry,
) -> str:

    return clean_text(
        entry.get("published")
        or entry.get("updated")
        or "Unknown"
    )


def get_source_name(
    entry,
    fallback: str,
) -> str:

    try:

        source = entry.get(
            "source"
        )

        if source:

            source_title = source.get(
                "title"
            )

            if source_title:

                return clean_text(
                    source_title
                )

    except Exception:
        pass

    return fallback


# =========================================================
# ROLE RELEVANCE FILTER
#
# This is the extra safety layer.
#
# Google Search already searches by role,
# but this removes obviously unrelated results.
# =========================================================

def is_relevant_to_role(
    article: CollectedArticle,
    user_role: str,
) -> bool:

    selected_role = normalize_role(
        user_role
    )

    if selected_role == "General Reader":

        return True

    keywords = ROLE_CONFIG[
        selected_role
    ]["keywords"]

    searchable_text = (
        f"{article.title} "
        f"{article.summary}"
    ).lower()

    return any(
        keyword.lower()
        in searchable_text

        for keyword
        in keywords
    )


# =========================================================
# CACHE READ
# =========================================================

def get_cached_feed(
    feed_url: str,
):

    with _cache_lock:

        cached = _feed_cache.get(
            feed_url
        )

        if cached is None:
            return None

        cached_time, articles = cached

        cache_age = (
            time.time()
            - cached_time
        )

        if cache_age > CACHE_TTL_SECONDS:

            return None

        return list(
            articles
        )


# =========================================================
# CACHE WRITE
# =========================================================

def save_cached_feed(
    feed_url: str,
    articles: List[CollectedArticle],
):

    with _cache_lock:

        _feed_cache[
            feed_url
        ] = (
            time.time(),
            list(articles),
        )


# =========================================================
# FETCH ONE RSS FEED
# =========================================================

def fetch_feed_from_network(
    source_name: str,
    feed_url: str,
) -> List[CollectedArticle]:

    started = time.perf_counter()

    try:

        response = requests.get(
            feed_url,

            timeout=(
                REQUEST_TIMEOUT_SECONDS
            ),

            headers={
                "User-Agent": (
                    "Mozilla/5.0 "
                    "NewsPulseAI/1.0"
                ),
                "Accept": (
                    "application/rss+xml,"
                    "application/xml,"
                    "text/xml,*/*"
                ),
            },
        )

        response.raise_for_status()

        parsed = feedparser.parse(
            response.content
        )

        collected = []

        for entry in parsed.entries[
            :MAX_ARTICLES_TO_SCAN_PER_FEED
        ]:

            title = get_title(
                entry
            )

            if not title:
                continue

            article = (
                CollectedArticle(
                    title=title,

                    summary=get_summary(
                        entry
                    ),

                    source=get_source_name(
                        entry,
                        source_name,
                    ),

                    link=clean_text(
                        entry.get(
                            "link",
                            "",
                        )
                    ),

                    published=get_published(
                        entry
                    ),
                )
            )

            collected.append(
                article
            )

        save_cached_feed(
            feed_url,
            collected,
        )

        elapsed = (
            time.perf_counter()
            - started
        )

        print(
            f"[RSS NETWORK] "
            f"{source_name}: "
            f"{len(collected)} articles "
            f"in {elapsed:.2f}s"
        )

        return collected

    except Exception as error:

        print(
            f"[RSS ERROR] "
            f"{source_name}: "
            f"{error}"
        )

        return []


# =========================================================
# GET FEED
#
# Uses cache when possible.
# =========================================================

def collect_from_feed(
    source_name: str,
    feed_url: str,
    user_role: str,
    limit: int,
) -> List[CollectedArticle]:

    cached = get_cached_feed(
        feed_url
    )

    if cached is not None:

        print(
            f"[RSS CACHE] "
            f"{source_name}"
        )

        candidates = cached

    else:

        candidates = (
            fetch_feed_from_network(
                source_name=source_name,

                feed_url=feed_url,
            )
        )


    relevant = []

    for article in candidates:

        if not is_relevant_to_role(
            article,
            user_role,
        ):
            continue

        relevant.append(
            article
        )

        if len(relevant) >= limit:
            break


    return relevant


# =========================================================
# NORMALIZE TITLE
# =========================================================

def normalize_title(
    title: str,
) -> str:

    title = (
        title
        or ""
    ).lower()

    title = re.sub(
        r"[^a-z0-9\s]",
        " ",
        title,
    )

    title = re.sub(
        r"\s+",
        " ",
        title,
    )

    return title.strip()


# =========================================================
# REMOVE EXACT DUPLICATES
# =========================================================

def remove_exact_duplicates(
    articles: List[CollectedArticle],
) -> List[CollectedArticle]:

    seen_titles = set()

    unique_articles = []

    for article in articles:

        normalized = normalize_title(
            article.title
        )

        if not normalized:
            continue

        if normalized in seen_titles:
            continue

        seen_titles.add(
            normalized
        )

        unique_articles.append(
            article
        )

    return unique_articles


# =========================================================
# MAIN COLLECTOR
#
# IMPORTANT:
#
# Existing main.py can still call:
#
# collect_latest_news(limit_per_source=3)
#
# and it defaults to General Reader.
#
# Orchestrator can now call:
#
# collect_latest_news(
#     limit_per_source=2,
#     user_role="Student"
# )
# =========================================================

def collect_latest_news(
    limit_per_source: int = 3,
    user_role: str = "General Reader",
) -> List[CollectedArticle]:

    started = time.perf_counter()

    selected_role = normalize_role(
        user_role
    )

    limit_per_source = max(
        1,
        int(limit_per_source),
    )

    feeds = get_feeds_for_role(
        selected_role
    )

    print()
    print(
        "========================================"
    )
    print(
        "NEWSPULSE ROLE-BASED NEWS COLLECTOR"
    )
    print(
        "ROLE:",
        selected_role
    )
    print(
        "SOURCES:",
        len(feeds)
    )
    print(
        "========================================"
    )

    all_articles = []

    worker_count = min(
        MAX_PARALLEL_FEEDS,
        len(feeds),
    )

    # =====================================================
    # PARALLEL RSS REQUESTS
    # =====================================================

    with ThreadPoolExecutor(
        max_workers=worker_count
    ) as executor:

        future_map = {}

        for feed in feeds:

            future = executor.submit(
                collect_from_feed,

                feed["name"],

                feed["url"],

                selected_role,

                limit_per_source,
            )

            future_map[
                future
            ] = feed["name"]


        for future in as_completed(
            future_map
        ):

            source_name = (
                future_map[
                    future
                ]
            )

            try:

                articles = future.result()

                all_articles.extend(
                    articles
                )

            except Exception as error:

                print(
                    f"[RSS WORKER ERROR] "
                    f"{source_name}: "
                    f"{error}"
                )


    all_articles = (
        remove_exact_duplicates(
            all_articles
        )
    )

    elapsed = (
        time.perf_counter()
        - started
    )

    print()
    print(
        f"[NEWS COLLECTOR COMPLETE] "
        f"{selected_role}: "
        f"{len(all_articles)} articles "
        f"in {elapsed:.2f}s"
    )

    print(
        "========================================"
    )

    return all_articles