from typing import Optional, Set, Tuple

import numpy as np

from models.schemas import LivingStory

from services.story_memory import (
    get_all_stories
)

from services.story_cluster import (
    get_embedding_model
)


# =====================================================
# CREATE TEXT FOR OLD STORY
# =====================================================

def living_story_to_text(
    story: LivingStory
) -> str:

    return (
        f"{story.title}. "
        f"{story.latest_briefing.headline}. "
        f"{story.latest_briefing.summary}. "
        f"{story.latest_briefing.what_happened}"
    )


# =====================================================
# FIND MATCHING STORY
# =====================================================

def find_matching_story(
    new_story_text: str,
    threshold: float = 0.58,
    excluded_story_ids: Optional[Set[str]] = None
) -> Tuple[Optional[LivingStory], float]:

    all_stories = get_all_stories()

    if not all_stories:

        return None, 0.0


    if excluded_story_ids is None:

        excluded_story_ids = set()


    available_stories = [

        story

        for story in all_stories

        if story.story_id
        not in excluded_story_ids
    ]


    if not available_stories:

        return None, 0.0


    old_story_texts = [

        living_story_to_text(
            story
        )

        for story in available_stories
    ]


    texts = [
        new_story_text,
        *old_story_texts
    ]


    model = get_embedding_model()


    embeddings = model.encode(
        texts,
        normalize_embeddings=True
    )


    new_embedding = embeddings[
        0
    ]


    old_embeddings = embeddings[
        1:
    ]


    similarities = np.dot(
        old_embeddings,
        new_embedding
    )


    best_index = int(
        np.argmax(
            similarities
        )
    )


    best_score = float(
        similarities[
            best_index
        ]
    )


    best_story = available_stories[
        best_index
    ]


    if best_score >= threshold:

        return (
            best_story,
            best_score
        )


    return (
        None,
        best_score
    )