from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ChecklistItem(BaseModel):
    """Checklist项"""
    item: str = Field(..., description="检查项")
    method: str = Field(..., description="检查方法")
    pass_criteria: str = Field(..., description="通过标准")
    risk_level: str = Field(default="medium", description="风险等级: high/medium/low")
    category: str = Field(default="general", description="分类")
    is_ai_generated: bool = Field(default=True, description="是否AI生成")


class ChecklistCheckRequest(BaseModel):
    """更新Checklist检查状态"""
    checklist_id: str = Field(..., alias="checklistId")
    is_checked: bool = Field(..., alias="isChecked")
    check_result: Optional[str] = Field(None, alias="checkResult", description="检查结果")
    checked_by: Optional[str] = Field(None, alias="checkedBy")

    model_config = {"populate_by_name": True}


class SubmissionCreate(BaseModel):
    """创建提测申请"""
    version: str = Field(..., description="提测版本")
    submission_type: str = Field(default="feature", alias="submissionType")
    requirement_id: Optional[str] = Field(None, alias="requirementId")
    requirement_link: Optional[str] = Field(None, alias="requirementLink")
    change_description: str = Field(..., alias="changeDescription")
    affected_modules: list[str] = Field(default_factory=list, alias="affectedModules")
    change_type: str = Field(default="modified", alias="changeType")
    self_test_passed: bool = Field(default=False, alias="selfTestPassed")
    self_test_case_count: int = Field(default=0, alias="selfTestCaseCount")
    self_test_coverage: Optional[int] = Field(None, alias="selfTestCoverage")
    self_test_conclusion: Optional[str] = Field(None, alias="selfTestConclusion")
    smoke_test_result: str = Field(default="not_executed", alias="smokeTestResult")
    blocking_issue_count: int = Field(default=0, alias="blockingIssueCount")
    git_diff: Optional[str] = Field(None, alias="gitDiff")
    git_commit_hash: Optional[str] = Field(None, alias="gitCommitHash")
    branch_name: Optional[str] = Field(None, alias="branchName")
    submitter: Optional[str] = None

    model_config = {"populate_by_name": True}


class ChecklistItemResponse(BaseModel):
    """Checklist项响应"""
    id: str
    item: str
    check_method: str = Field(alias="checkMethod")
    pass_criteria: str = Field(alias="passCriteria")
    risk_level: str = Field(alias="riskLevel")
    category: str
    is_checked: bool = Field(alias="isChecked")
    check_result: Optional[str] = Field(None, alias="checkResult")
    checked_by: Optional[str] = Field(None, alias="checkedBy")
    checked_at: Optional[datetime] = Field(None, alias="checkedAt")
    is_ai_generated: bool = Field(alias="isAiGenerated")

    model_config = {"populate_by_name": True}


class SubmissionItem(BaseModel):
    """提测申请详情"""
    id: str
    version: str = Field(alias="version")
    submission_type: str = Field(alias="submissionType")
    requirement_id: Optional[str] = Field(None, alias="requirementId")
    requirement_link: Optional[str] = Field(None, alias="requirementLink")
    change_description: str = Field(alias="changeDescription")
    affected_modules: list[str] = Field(default_factory=list, alias="affectedModules")
    change_type: str = Field(alias="changeType")
    self_test_passed: bool = Field(alias="selfTestPassed")
    self_test_case_count: int = Field(alias="selfTestCaseCount")
    self_test_coverage: Optional[int] = Field(None, alias="selfTestCoverage")
    self_test_conclusion: Optional[str] = Field(None, alias="selfTestConclusion")
    smoke_test_result: str = Field(alias="smokeTestResult")
    blocking_issue_count: int = Field(alias="blockingIssueCount")
    status: str
    gate_result: Optional[dict] = Field(None, alias="gateResult")
    gate_reject_reason: Optional[str] = Field(None, alias="gateRejectReason")
    git_diff: Optional[str] = Field(None, alias="gitDiff")
    git_commit_hash: Optional[str] = Field(None, alias="gitCommitHash")
    branch_name: Optional[str] = Field(None, alias="branchName")
    submitter: Optional[str] = None
    reviewed_by: Optional[str] = Field(None, alias="reviewedBy")
    created_at: datetime = Field(alias="createdAt")
    updated_at: Optional[datetime] = Field(None, alias="updatedAt")
    checklists: list[ChecklistItemResponse] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class GenerateChecklistRequest(BaseModel):
    """AI生成Checklist请求"""
    submission_id: str = Field(..., alias="submissionId")
    change_description: str = Field(..., alias="changeDescription")
    affected_modules: list[str] = Field(default_factory=list, alias="affectedModules")
    git_diff: Optional[str] = Field(None, alias="gitDiff")
    recent_defects: Optional[list[str]] = Field(None, alias="recentDefects")

    model_config = {"populate_by_name": True}


class GenerateChecklistResponse(BaseModel):
    """AI生成Checklist响应"""
    checklists: list[ChecklistItem]
    summary: str
    suggestions: list[str]
    high_risk_areas: list[str] = Field(default_factory=list, alias="highRiskAreas")

    model_config = {"populate_by_name": True}


class SubmissionListResponse(BaseModel):
    """提测申请列表"""
    items: list[SubmissionItem]
    total: int
    page: int
    page_size: int = Field(alias="pageSize")

    model_config = {"populate_by_name": True}


class SubmissionUpdate(BaseModel):
    """更新提测申请"""
    status: Optional[str] = None
    self_test_passed: Optional[bool] = Field(None, alias="selfTestPassed")
    self_test_case_count: Optional[int] = Field(None, alias="selfTestCaseCount")
    self_test_coverage: Optional[int] = Field(None, alias="selfTestCoverage")
    self_test_conclusion: Optional[str] = Field(None, alias="selfTestConclusion")
    smoke_test_result: Optional[str] = Field(None, alias="smokeTestResult")
    blocking_issue_count: Optional[int] = Field(None, alias="blockingIssueCount")
    gate_result: Optional[str] = Field(None, alias="gateResult")
    gate_reject_reason: Optional[str] = Field(None, alias="gateRejectReason")
    reviewed_by: Optional[str] = Field(None, alias="reviewedBy")
    submitter: Optional[str] = None

    model_config = {"populate_by_name": True}
