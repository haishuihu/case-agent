from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.testcase import GenerationMetadata, ReviewQuestion, TestCaseItem


class ReviewModuleItem(BaseModel):
    id: str
    name: str
    description: str
    sub_features: list[str] = Field(default_factory=list, alias="subFeatures")

    model_config = {"populate_by_name": True}


class ReviewResponse(BaseModel):
    modules: list[ReviewModuleItem]
    questions: list[ReviewQuestion]
    business_rules: list[str] = Field(default_factory=list, alias="businessRules")
    data_constraints: list[dict[str, object]] = Field(default_factory=list, alias="dataConstraints")
    model_name: str = Field(alias="modelName")

    model_config = {"populate_by_name": True}


class RequirementSummaryResponse(BaseModel):
    summary_text: str = Field(alias="summaryText")
    modules: list[str] = Field(default_factory=list)
    business_rules: list[str] = Field(default_factory=list, alias="businessRules")
    data_constraints: list[str] = Field(default_factory=list, alias="dataConstraints")
    open_questions: list[str] = Field(default_factory=list, alias="openQuestions")
    model_name: str = Field(alias="modelName")

    model_config = {"populate_by_name": True}


class GenerateResponse(BaseModel):
    generation_id: str = Field(alias="generationId")
    markdown: str
    model_name: str = Field(alias="modelName")
    attachment_count: int = Field(alias="attachmentCount")
    created_at: datetime = Field(alias="createdAt")
    cases: list[TestCaseItem]
    metadata: GenerationMetadata

    model_config = {"populate_by_name": True}


class TaskSubmitResponse(BaseModel):
    task_id: str = Field(alias="taskId")
    status: str

    model_config = {"populate_by_name": True}


class TaskStatusResponse(BaseModel):
    task_id: str = Field(alias="taskId")
    status: str
    current_phase: str = Field(alias="currentPhase")
    phase_label: str = Field(alias="phaseLabel")
    progress: float
    phases: list[dict[str, object]]
    elapsed_seconds: int = Field(alias="elapsedSeconds")
    result: Optional[GenerateResponse] = None
    error_message: Optional[str] = Field(default=None, alias="errorMessage")
    requirement_preview: Optional[str] = Field(
        default=None,
        alias="requirementPreview",
        description="First ~80 chars of requirement for history list",
    )
    case_count: Optional[int] = Field(default=None, alias="caseCount")

    model_config = {"populate_by_name": True}


class TaskListItem(BaseModel):
    task_id: str = Field(alias="taskId")
    status: str
    requirement_preview: str = Field(alias="requirementPreview")
    case_count: Optional[int] = Field(default=None, alias="caseCount")
    created_at: datetime = Field(alias="createdAt")
    model_name: Optional[str] = Field(default=None, alias="modelName")

    model_config = {"populate_by_name": True}


class TaskListResponse(BaseModel):
    items: list[TaskListItem]
    total: int
    page: int
    page_size: int = Field(alias="pageSize")

    model_config = {"populate_by_name": True}
