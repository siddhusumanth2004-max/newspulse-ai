from models.schemas import CollectedArticle

from services.story_cluster import cluster_articles


# =====================================================
# TEST ARTICLES
# =====================================================

articles = [

    CollectedArticle(
        title="OpenAI launches new AI model for developers",
        summary="OpenAI announced a new artificial intelligence model designed for developers.",
        source="Source A",
        link="https://example.com/1",
        published="Today"
    ),

    CollectedArticle(
        title="OpenAI announces latest AI model aimed at developers",
        summary="The company introduced a new AI model with tools for software developers.",
        source="Source B",
        link="https://example.com/2",
        published="Today"
    ),

    CollectedArticle(
        title="New OpenAI model released with developer API access",
        summary="OpenAI released its latest model and announced API availability.",
        source="Source C",
        link="https://example.com/3",
        published="Today"
    ),

    CollectedArticle(
        title="India wins cricket match against Australia",
        summary="India defeated Australia in an international cricket match.",
        source="Source D",
        link="https://example.com/4",
        published="Today"
    ),

    CollectedArticle(
        title="Indian cricket team defeats Australia",
        summary="India secured victory over Australia in today's cricket match.",
        source="Source E",
        link="https://example.com/5",
        published="Today"
    )
]


# =====================================================
# RUN CLUSTERING
# =====================================================

result = cluster_articles(
    articles=articles,
    similarity_threshold=0.50
)


# =====================================================
# SHOW RESULT
# =====================================================

print()
print("====================================")
print("STORY CLUSTER TEST")
print("====================================")

print(
    "Total Articles:",
    result.total_articles
)

print(
    "Total Clusters:",
    result.total_clusters
)

print()


for cluster in result.clusters:

    print(
        f"CLUSTER {cluster.cluster_id}"
    )

    print(
        "Article Count:",
        cluster.article_count
    )

    print(
        "Representative:",
        cluster.representative_title
    )

    print()

    for article in cluster.articles:

        print(
            "-",
            article.title
        )

    print()
    print(
        "------------------------------------"
    )