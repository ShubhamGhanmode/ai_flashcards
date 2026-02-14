"""Prompt templates for LLM generation."""

# =============================================================================
# Deck Generation Prompts
# =============================================================================

DECK_SYSTEM_PROMPT_V1 = """You are an expert educational content creator.
Your task is to create a set of flashcard concepts for learning.

Rules:
1. Generate between 3-7 concept cards based on the topic.
2. Each concept must have exactly 5 bullet points.
3. Bullets should progress from basic to more nuanced understanding.
4. Set example_possible to true only if a concrete example would help.
5. If example_possible is true, provide a brief example_hint.
6. Keep bullet points concise (under 100 characters each).
7. Ensure concepts are distinct and don't overlap.
8. Match content difficulty to the specified level.

Output valid JSON only. No markdown, no code blocks."""


DECK_USER_PROMPT_V1 = """Create flashcard concepts for:

Topic: {topic}
Difficulty: {difficulty_level}
Number of concepts: {max_concepts}
{scope_line}

Generate educational flashcard concepts following the schema exactly."""


# =============================================================================
# Example Generation Prompts
# =============================================================================

EXAMPLE_SYSTEM_PROMPT_V1 = """You are an expert tutor creating examples for one flashcard concept.
Your task is to provide a concise, educational example grounded in the provided card.

Rules:
1. Stay grounded in the card title and bullet points.
2. Do not contradict the card bullets.
3. Match the requested style and length.
4. Include optional steps/pitfalls only if they improve clarity.
5. Follow user constraints when they are safe and relevant.
6. Keep the response practical and easy to apply.

Output valid JSON only. No markdown, no code blocks."""


EXAMPLE_USER_PROMPT_V1 = """Create an example for this flashcard concept:

Title: {title}
Bullets:
{bullets_text}
{hint_line}
Style: {style}
Length: {length}
Constraints:
{constraints_text}

Generate the example output following the schema exactly."""


# =============================================================================
# Prompt Version Tracking
# =============================================================================

PROMPT_VERSIONS = {
    "deck_system": "v1",
    "deck_user": "v1",
    "example_system": "v1",
    "example_user": "v1",
}


def get_deck_prompts(
    topic: str,
    difficulty_level: str,
    max_concepts: int,
    scope: str | None = None,
) -> tuple[str, str]:
    """Get system and user prompts for deck generation."""
    scope_line = f"Scope: {scope}" if scope else ""
    user_prompt = DECK_USER_PROMPT_V1.format(
        topic=topic,
        difficulty_level=difficulty_level,
        max_concepts=max_concepts,
        scope_line=scope_line,
    )
    return DECK_SYSTEM_PROMPT_V1, user_prompt


def get_example_prompts(
    *,
    title: str,
    bullets: list[str],
    example_hint: str | None,
    style: str,
    length: str,
    constraints: list[str] | None,
) -> tuple[str, str]:
    """Get system and user prompts for example generation."""
    bullets_text = "\n".join(f"- {bullet}" for bullet in bullets)
    hint_line = f"Hint: {example_hint}\n" if example_hint else ""
    constraints_text = (
        "\n".join(f"- {constraint}" for constraint in constraints)
        if constraints
        else "- None"
    )
    user_prompt = EXAMPLE_USER_PROMPT_V1.format(
        title=title,
        bullets_text=bullets_text,
        hint_line=hint_line,
        style=style,
        length=length,
        constraints_text=constraints_text,
    )
    return EXAMPLE_SYSTEM_PROMPT_V1, user_prompt
