import re
import html
import feedparser

from models.schemas import CollectedArticle


# =====================================================
# MULTI-SOURCE NEWS FEEDS
# =====================================================

NEWS_FEEDS = [

    {
        "name": "Google News India",
        "url": "https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en"
    },

    {
        "name": "Google News Technology",
        "url": "https://news.google.com/rss/headlines/section/topic/TECHNOLOGY?hl=en-IN&gl=IN&ceid=IN:en"
    },

    {
        "name": "BBC World",
        "url": "https://feeds.bbci.co.uk/news/world/rss.xml"
    },

    {
        "name": "BBC Technology",
        "url": "https://feeds.bbci.co.uk/news/technology/rss.xml"
    },

    {
        "name": "The Verge",
        "url": "https://www.theverge.com/rss/index.xml"
    },

    {
        "name": "TechCrunch",
        "url": "https://techcrunch.com/feed/"
    }
]


# =====================================================
# CLEAN TEXT
# =====================================================

def clean_text(text: str) -> str:

    if not text:
        return ""

    text = html.unescape(text)

    text = re.sub(
        r"<[^>]+>",
        " ",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# =====================================================
# PUBLISHED DATE
# =====================================================

def get_published(entry) -> str:

    published = entry.get(
        "published",
        ""
    )

    if published:
        return published

    updated = entry.get(
        "updated",
        ""
    )

    if updated:
        return updated

    return "Unknown"


# =====================================================
# GET ARTICLE TITLE
# =====================================================

def get_title(entry) -> str:

    return clean_text(
        entry.get(
            "title",
            "Untitled"
        )
    )


# =====================================================
# GET ARTICLE SUMMARY
# =====================================================

def get_summary(entry) -> str:

    summary = entry.get(
        "summary",
        ""
    )

    if not summary:

        summary = entry.get(
            "description",
            ""
        )

    return clean_text(
        summary
    )


# =====================================================
# COLLECT ONE FEED
# =====================================================

def collect_from_feed(
    source_name: str,
    feed_url: str,
    limit: int
):

    print(
        f"Collecting news from: {source_name}"
    )

    parsed = feedparser.parse(
        feed_url
    )

    collected = []

    for entry in parsed.entries[:limit]:

        title = get_title(
            entry
        )

        summary = get_summary(
            entry
        )

        link = entry.get(
            "link",
            ""
        )

        published = get_published(
            entry
        )

        if not title:
            continue

        collected.append(

            CollectedArticle(
                title=title,
                summary=summary,
                source=source_name,
                link=link,
                published=published
            )

        )

    print(
        f"{source_name}: {len(collected)} articles"
    )

    return collected


# =====================================================
# NORMALIZE TITLE
# =====================================================

def normalize_title(
    title: str
) -> str:

    title = title.lower()

    title = re.sub(
        r"[^a-z0-9\s]",
        " ",
        title
    )

    title = re.sub(
        r"\s+",
        " ",
        title
    )

    return title.strip()


# =====================================================
# REMOVE EXACT DUPLICATES
# =====================================================

def remove_exact_duplicates(
    articles
):

    seen = set()

    unique_articles = []

    for article in articles:

        normalized = normalize_title(
            article.title
        )

        if normalized in seen:
            continue

        seen.add(
            normalized
        )

        unique_articles.append(
            article
        )

    return unique_articles


# =====================================================
# COLLECT ALL LATEST NEWS
# =====================================================

def collect_latest_news(
    limit_per_source: int = 5
):

    all_articles = []

    for feed in NEWS_FEEDS:

        try:

            articles = collect_from_feed(
                source_name=feed["name"],
                feed_url=feed["url"],
                limit=limit_per_source
            )

            all_articles.extend(
                articles
            )

        except Exception as error:

            print(
                f"NEWS COLLECTION ERROR [{feed['name']}]:",
                error
            )

    # Remove only exact duplicate headlines.
    # Semantic duplicates will be handled by
    # Story Clustering later.

    all_articles = remove_exact_duplicates(
        all_articles
    )

    return all_articles