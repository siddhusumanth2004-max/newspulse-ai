from typing import List

import numpy as np

from sentence_transformers import SentenceTransformer

from models.schemas import (
    CollectedArticle,
    StoryCluster,
    StoryClusteringResponse
)


# =====================================================
# EMBEDDING MODEL
# =====================================================

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

_embedding_model = None


def get_embedding_model():

    global _embedding_model

    if _embedding_model is None:

        print(
            "Loading story clustering model:",
            MODEL_NAME
        )

        _embedding_model = SentenceTransformer(
            MODEL_NAME
        )

        print(
            "Story clustering model loaded successfully."
        )

    return _embedding_model


# =====================================================
# CREATE TEXT USED FOR SIMILARITY
# =====================================================

def article_to_text(
    article: CollectedArticle
) -> str:

    title = article.title or ""
    summary = article.summary or ""

    return f"{title}. {summary}".strip()


# =====================================================
# COSINE SIMILARITY
# =====================================================

def cosine_similarity(
    vector_a,
    vector_b
) -> float:

    vector_a = np.array(
        vector_a
    )

    vector_b = np.array(
        vector_b
    )

    denominator = (
        np.linalg.norm(vector_a)
        *
        np.linalg.norm(vector_b)
    )

    if denominator == 0:
        return 0.0

    return float(
        np.dot(
            vector_a,
            vector_b
        ) / denominator
    )


# =====================================================
# STORY CLUSTERING
# =====================================================

def cluster_articles(
    articles: List[CollectedArticle],
    similarity_threshold: float = 0.65
) -> StoryClusteringResponse:

    if not articles:

        return StoryClusteringResponse(
            total_articles=0,
            total_clusters=0,
            clusters=[]
        )

    # -------------------------------------------------
    # Convert articles into text
    # -------------------------------------------------

    article_texts = [
        article_to_text(article)
        for article in articles
    ]

    # -------------------------------------------------
    # Generate embeddings
    # -------------------------------------------------

    model = get_embedding_model()

    embeddings = model.encode(
        article_texts,
        normalize_embeddings=True
    )

    clusters = []

    cluster_embeddings = []

    # -------------------------------------------------
    # Greedy clustering
    # -------------------------------------------------

    for article_index, article in enumerate(
        articles
    ):

        current_embedding = embeddings[
            article_index
        ]

        best_cluster_index = None

        best_similarity = 0.0

        # Compare article against existing clusters
        for cluster_index, cluster_embedding in enumerate(
            cluster_embeddings
        ):

            similarity = cosine_similarity(
                current_embedding,
                cluster_embedding
            )

            if similarity > best_similarity:

                best_similarity = similarity

                best_cluster_index = cluster_index

        # -------------------------------------------------
        # Add article to existing cluster
        # -------------------------------------------------

        if (
            best_cluster_index is not None
            and
            best_similarity >= similarity_threshold
        ):

            clusters[
                best_cluster_index
            ].append(
                article
            )

            # Recalculate cluster center
            cluster_article_embeddings = []

            for cluster_article in clusters[
                best_cluster_index
            ]:

                cluster_article_index = articles.index(
                    cluster_article
                )

                cluster_article_embeddings.append(
                    embeddings[
                        cluster_article_index
                    ]
                )

            cluster_embeddings[
                best_cluster_index
            ] = np.mean(
                cluster_article_embeddings,
                axis=0
            )

        # -------------------------------------------------
        # Create new cluster
        # -------------------------------------------------

        else:

            clusters.append(
                [
                    article
                ]
            )

            cluster_embeddings.append(
                current_embedding
            )

    # -------------------------------------------------
    # Convert to response models
    # -------------------------------------------------

    story_clusters = []

    for index, cluster in enumerate(
        clusters,
        start=1
    ):

        representative_title = cluster[
            0
        ].title

        story_cluster = StoryCluster(
            cluster_id=index,
            representative_title=representative_title,
            article_count=len(
                cluster
            ),
            articles=cluster
        )

        story_clusters.append(
            story_cluster
        )

    # Sort largest clusters first
    story_clusters.sort(
        key=lambda item: item.article_count,
        reverse=True
    )

    return StoryClusteringResponse(
        total_articles=len(
            articles
        ),
        total_clusters=len(
            story_clusters
        ),
        clusters=story_clusters
    )