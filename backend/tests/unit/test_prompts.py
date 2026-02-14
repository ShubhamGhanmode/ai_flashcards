"""Tests for prompt registry."""

from app.prompts.registry import (
    PROMPT_VERSIONS,
    get_deck_prompts,
    get_example_prompts,
)


class TestPromptRegistry:
    """Tests for prompt template generation."""

    def test_get_deck_prompts_returns_tuple(self) -> None:
        system, user = get_deck_prompts(
            topic="Binary Search Trees",
            difficulty_level="beginner",
            max_concepts=5,
        )
        assert isinstance(system, str)
        assert isinstance(user, str)

    def test_user_prompt_contains_topic(self) -> None:
        _, user = get_deck_prompts(
            topic="Photosynthesis",
            difficulty_level="intermediate",
            max_concepts=5,
        )
        assert "Photosynthesis" in user

    def test_user_prompt_contains_difficulty(self) -> None:
        _, user = get_deck_prompts(
            topic="Test",
            difficulty_level="advanced",
            max_concepts=3,
        )
        assert "advanced" in user

    def test_user_prompt_contains_max_concepts(self) -> None:
        _, user = get_deck_prompts(
            topic="Test",
            difficulty_level="beginner",
            max_concepts=7,
        )
        assert "7" in user

    def test_scope_included_when_provided(self) -> None:
        _, user = get_deck_prompts(
            topic="Physics",
            difficulty_level="beginner",
            max_concepts=5,
            scope="Newtonian Mechanics",
        )
        assert "Newtonian Mechanics" in user

    def test_scope_excluded_when_none(self) -> None:
        _, user = get_deck_prompts(
            topic="Physics",
            difficulty_level="beginner",
            max_concepts=5,
            scope=None,
        )
        assert "Scope:" not in user

    def test_prompt_versions_exist(self) -> None:
        assert "deck_system" in PROMPT_VERSIONS
        assert "deck_user" in PROMPT_VERSIONS
        assert "example_system" in PROMPT_VERSIONS
        assert "example_user" in PROMPT_VERSIONS

    def test_system_prompt_mentions_rules(self) -> None:
        system, _ = get_deck_prompts(
            topic="Test",
            difficulty_level="beginner",
            max_concepts=5,
        )
        assert "5 bullet" in system.lower() or "bullet point" in system.lower()

    def test_example_prompt_contains_card_context(self) -> None:
        _, user = get_example_prompts(
            title="Binary Search Tree",
            bullets=["Definition", "Insertion", "Search"],
            example_hint="Walk through insertion order.",
            style="analogy",
            length="short",
            constraints=["Use everyday language"],
        )
        assert "Binary Search Tree" in user
        assert "analogy" in user
        assert "short" in user
        assert "Use everyday language" in user
        assert "Walk through insertion order." in user

    def test_example_prompt_uses_none_constraints_when_missing(self) -> None:
        _, user = get_example_prompts(
            title="Topic",
            bullets=["Point A"],
            example_hint=None,
            style="default",
            length="medium",
            constraints=None,
        )
        assert "- None" in user
