"""Pydantic schemas for card example generation."""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SchemaBase(BaseModel):
    """Base schema that forbids unknown fields."""

    model_config = ConfigDict(extra="forbid")


Constraint = Annotated[str, Field(min_length=1, max_length=200)]
StepItem = Annotated[str, Field(min_length=1, max_length=300)]
PitfallItem = Annotated[str, Field(min_length=1, max_length=200)]
SourceRef = Annotated[str, Field(min_length=1, max_length=50)]


class ExampleGenerateRequest(SchemaBase):
    """Request model for generating a card example."""

    style: Literal["default", "analogy", "real_world"] = "default"
    length: Literal["short", "medium", "long"] = "medium"
    constraints: Annotated[list[Constraint] | None, Field(max_length=10)] = None


class TokenUsage(SchemaBase):
    """Token usage statistics."""

    prompt: int = Field(..., ge=0)
    completion: int = Field(..., ge=0)
    total: int = Field(..., ge=0)


class GenerationMetadata(SchemaBase):
    """Metadata about the generation process."""

    model: str
    prompt_version: str
    tokens: TokenUsage
    timestamp: datetime
    rag_used: bool = False


class ExampleResponse(SchemaBase):
    """Response model for generated card examples."""

    schema_version: Literal["1.0"] = "1.0"
    card_id: UUID
    example: Annotated[str, Field(min_length=1, max_length=2000)]
    steps: Annotated[list[StepItem] | None, Field(max_length=10)] = None
    pitfalls: Annotated[list[PitfallItem] | None, Field(max_length=5)] = None
    source_refs: list[SourceRef] | None = None
    generation_metadata: GenerationMetadata


class LLMExampleOutput(SchemaBase):
    """Structured LLM output for example generation."""

    example: Annotated[str, Field(min_length=1, max_length=2000)]
    steps: Annotated[list[StepItem] | None, Field(max_length=10)] = None
    pitfalls: Annotated[list[PitfallItem] | None, Field(max_length=5)] = None
    source_refs: list[SourceRef] | None = None
