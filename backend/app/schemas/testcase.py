from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class TestCaseItem(BaseModel):
    summary: str
    priority: str = "P2"
    module: str = ""
    category: str = ""
    confirmation_note: Optional[str] = Field(default=None, alias="confirmationNote")

    model_config = {"populate_by_name": True}


class ReviewQuestion(BaseModel):
    id: str
    question_type: str = Field(alias="questionType")
    description: str
    module: str = ""
    suggestion: str = ""

    model_config = {"populate_by_name": True}


class GenerationMetadata(BaseModel):
    case_count: int = Field(alias="caseCount")
    category_counts: dict[str, int] = Field(alias="categoryCounts")
    module_counts: dict[str, int] = Field(default_factory=dict, alias="moduleCounts")
    priority_counts: dict[str, int] = Field(default_factory=dict, alias="priorityCounts")
    review_questions: list[ReviewQuestion] = Field(default_factory=list, alias="reviewQuestions")
    warnings: list[str] = Field(default_factory=list)
    truncated: bool = False
    incomplete_categories: list[str] = Field(default_factory=list, alias="incompleteCategories")

    model_config = {"populate_by_name": True}
