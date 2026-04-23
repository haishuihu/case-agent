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


class QuickGenerateResponse(BaseModel):
    """极简模式快速生成响应"""
    content: str = Field(..., description="Markdown 格式的测试要点内容")
    model_name: str = Field(alias="modelName")
    generated_at: datetime = Field(alias="generatedAt")

    model_config = {"populate_by_name": True}


class QuickHistoryItem(BaseModel):
    id: str
    requirement_preview: str = Field(alias="requirementPreview")
    output_content: str = Field(alias="outputContent")
    model_name: str = Field(alias="modelName")
    created_at: datetime = Field(alias="createdAt")

    model_config = {"populate_by_name": True}


class QuickHistoryListResponse(BaseModel):
    items: list[QuickHistoryItem]
    total: int
    page: int
    page_size: int = Field(alias="pageSize")

    model_config = {"populate_by_name": True}


class QuickHistoryClearResponse(BaseModel):
    ok: bool = Field(alias="ok")
    deleted_count: int = Field(alias="deletedCount")

    model_config = {"populate_by_name": True}


class AppendGenerateRequest(BaseModel):
    """追加生成请求：已有用例 + 需求，AI 补充遗漏场景"""
    existing_cases: str = Field(..., alias="existingCases", description="已有用例内容（Markdown 格式）")
    requirement_text: str = Field(..., alias="requirementText", description="需求描述")
    model_key: Optional[str] = Field(None, alias="modelKey", description="模型Key")

    model_config = {"populate_by_name": True}


class AppendedCaseItem(BaseModel):
    """追加的用例项"""
    title: str = Field(..., description="用例标题")
    category: str = Field(..., description="分类")
    priority: str = Field(..., description="优先级")
    module: str = Field(..., description="所属模块")
    missing_reason: str = Field(..., description="为什么这个用例被遗漏")
    preconditions: list[str] = Field(default_factory=list, description="前置条件")
    steps: list[str] = Field(default_factory=list, description="测试步骤")
    expected_result: str = Field(..., alias="expectedResult", description="预期结果")

    model_config = {"populate_by_name": True}


class AppendGenerateResponse(BaseModel):
    """追加生成响应"""
    appended_cases: list[AppendedCaseItem] = Field(alias="appendedCases")
    total_count: int = Field(alias="totalCount")
    model_name: str = Field(alias="modelName")
    generated_at: datetime = Field(alias="generatedAt")
    summary: str = Field(..., description="补充说明")

    model_config = {"populate_by_name": True}
