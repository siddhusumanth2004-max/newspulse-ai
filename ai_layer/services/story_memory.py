import json
import uuid

from pathlib import Path
from datetime import datetime, timezone

from models.schemas import (
    LivingStory,
    StoryEvent,
    NewsBriefing,
    DeltaResponse
)

from agents.briefing_agent import generate_briefing
from agents.delta_agent import detect_changes


# =====================================================
# STORAGE
# =====================================================

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"

DATA_FILE = DATA_DIR / "stories.json"


DATA_DIR.mkdir(
    parents=True,
    exist_ok=True
)


if not DATA_FILE.exists():

    DATA_FILE.write_text(
        "{}",
        encoding="utf-8"
    )


# =====================================================
# HELPERS
# =====================================================

def current_time() -> str:

    return datetime.now(
        timezone.utc
    ).isoformat()


def model_to_dict(model):

    if hasattr(
        model,
        "model_dump"
    ):
        return model.model_dump()

    return model.dict()


def load_stories() -> dict:

    try:

        content = DATA_FILE.read_text(
            encoding="utf-8"
        )

        if not content.strip():
            return {}

        return json.loads(
            content
        )

    except Exception as error:

        print(
            "STORY LOAD ERROR:",
            error
        )

        return {}


def save_stories(
    stories: dict
):

    DATA_FILE.write_text(

        json.dumps(
            stories,
            indent=4,
            ensure_ascii=False
        ),

        encoding="utf-8"
    )


# =====================================================
# NORMAL MANUAL CREATE STORY
# =====================================================

def create_story(
    title: str,
    article: str,
    source_name: str
) -> LivingStory:

    briefing = generate_briefing(
        article
    )

    return create_story_with_analysis(
        title=title,
        article=article,
        source_name=source_name,
        briefing=briefing
    )


# =====================================================
# CREATE STORY USING EXISTING AI ANALYSIS
# =====================================================

def create_story_with_analysis(
    title: str,
    article: str,
    source_name: str,
    briefing: NewsBriefing
) -> LivingStory:

    stories = load_stories()

    story_id = str(
        uuid.uuid4()
    )

    now = current_time()

    first_event = StoryEvent(
        timestamp=now,
        source_name=source_name,
        article=article,
        briefing=briefing,
        delta=None
    )

    story = LivingStory(

        story_id=story_id,

        title=title,

        category=briefing.category,

        created_at=now,

        updated_at=now,

        latest_briefing=briefing,

        latest_article=article,

        total_updates=1,

        timeline=[
            first_event
        ]
    )

    stories[
        story_id
    ] = model_to_dict(
        story
    )

    save_stories(
        stories
    )

    return story


# =====================================================
# GET STORY
# =====================================================

def get_story(
    story_id: str
):

    stories = load_stories()

    story_data = stories.get(
        story_id
    )

    if not story_data:
        return None

    return LivingStory(
        **story_data
    )


# =====================================================
# GET ALL STORIES
# =====================================================

def get_all_stories():

    stories = load_stories()

    results = []

    for story_data in stories.values():

        try:

            results.append(
                LivingStory(
                    **story_data
                )
            )

        except Exception as error:

            print(
                "INVALID STORY DATA:",
                error
            )

    return results


# =====================================================
# NORMAL MANUAL UPDATE
# =====================================================

def update_story(
    story_id: str,
    article: str,
    source_name: str
):

    story = get_story(
        story_id
    )

    if not story:
        return None

    delta = detect_changes(
        previous_news=story.latest_article,
        current_news=article
    )

    briefing = generate_briefing(
        article
    )

    return update_story_with_analysis(
        story_id=story_id,
        article=article,
        source_name=source_name,
        briefing=briefing,
        delta=delta
    )


# =====================================================
# UPDATE STORY USING EXISTING AI ANALYSIS
# =====================================================

def update_story_with_analysis(
    story_id: str,
    article: str,
    source_name: str,
    briefing: NewsBriefing,
    delta: DeltaResponse
):

    stories = load_stories()

    story_data = stories.get(
        story_id
    )

    if not story_data:
        return None


    now = current_time()


    new_event = StoryEvent(

        timestamp=now,

        source_name=source_name,

        article=article,

        briefing=briefing,

        delta=delta
    )


    story_data[
        "updated_at"
    ] = now


    story_data[
        "latest_article"
    ] = article


    story_data[
        "latest_briefing"
    ] = model_to_dict(
        briefing
    )


    story_data[
        "category"
    ] = briefing.category


    story_data[
        "total_updates"
    ] = (
        story_data.get(
            "total_updates",
            0
        )
        + 1
    )


    if "timeline" not in story_data:

        story_data[
            "timeline"
        ] = []


    story_data[
        "timeline"
    ].append(
        model_to_dict(
            new_event
        )
    )


    stories[
        story_id
    ] = story_data


    save_stories(
        stories
    )


    return LivingStory(
        **story_data
    )