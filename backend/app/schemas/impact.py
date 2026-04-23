from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ImpactAnalysisRequest(BaseModel):
    """影响分析请求"""
    gitDiff: str = Field(..., description="Git Diff 内容")
    affectedModules: list[str] = Field(default_factory=list, description="影响模块列表")
    submissionId: Optional[str] = Field(None, description="关联提测申请ID")
    recentDefects: Optional[list[str]] = Field(None, description="最近相关缺陷列表")

    model_config = {"populate_by_name": True}


class ChangedFileItem(BaseModel):
    """变更文件项"""
    filename: str = Field(description="文件名")
    status: str = Field(description="状态: added/modified/deleted")
    additions: int = Field(default=0, description="新增行数")
    deletions: int = Field(default=0, description="删除行数")


class ImpactedModuleResponse(BaseModel):
    """受影响模块响应"""
    id: str
    moduleName: str = Field(alias="moduleName")
    moduleType: str = Field(alias="moduleType")
    riskLevel: str = Field(alias="riskLevel")
    impactDescription: Optional[str] = Field(None, alias="impactDescription")

    model_config = {"populate_by_name": True}


class RegressionRecommendationResponse(BaseModel):
    """回归推荐项响应"""
    id: str
    caseId: Optional[str] = Field(None, alias="caseId")
    caseTitle: Optional[str] = Field(None, alias="caseTitle")
    priority: str
    riskLevel: str = Field(alias="riskLevel")
    reason: Optional[str] = None
    estimatedMinutes: Optional[int] = Field(None, alias="estimatedMinutes")
    category: Optional[str] = None
    executionStatus: Optional[str] = Field(None, alias="executionStatus")

    model_config = {"populate_by_name": True}


class ImpactAnalysisResponse(BaseModel):
    """影响分析响应"""
    id: str
    submissionId: Optional[str] = Field(None, alias="submissionId")
    changedFiles: list[ChangedFileItem] = Field(alias="changedFiles")
    addedLines: int = Field(alias="addedLines")
    deletedLines: int = Field(alias="deletedLines")
    modifiedFunctions: list[str] = Field(alias="modifiedFunctions")
    impactedModules: list[ImpactedModuleResponse] = Field(alias="impactedModules")
    indirectImpacts: list[str] = Field(alias="indirectImpacts")
    apiBreakingChanges: list[str] = Field(alias="apiBreakingChanges")
    riskPoints: list[str] = Field(alias="riskPoints")
    confidenceLevel: str = Field(alias="confidenceLevel")
    summary: str
    recommendations: list[RegressionRecommendationResponse]
    estimatedTotalMinutes: int = Field(alias="estimatedTotalMinutes")
    createdAt: datetime = Field(alias="createdAt")

    model_config = {"populate_by_name": True}


class RegressionRecommendRequest(BaseModel):
    """回归推荐请求"""
    analysisId: Optional[str] = Field(None, alias="analysisId")
    submissionId: Optional[str] = Field(None, alias="submissionId")

    model_config = {"populate_by_name": True}


class RegressionRecommendResponse(BaseModel):
    """回归推荐响应"""
    analysisId: str = Field(alias="analysisId")
    mustRegress: list[RegressionRecommendationResponse] = Field(alias="mustRegress")
    shouldRegress: list[RegressionRecommendationResponse] = Field(alias="shouldRegress")
    couldRegress: list[RegressionRecommendationResponse] = Field(alias="couldRegress")
    totalMustMinutes: int = Field(alias="totalMustMinutes")
    totalShouldMinutes: int = Field(alias="totalShouldMinutes")
    totalCouldMinutes: int = Field(alias="totalCouldMinutes")

    model_config = {"populate_by_name": True}


class ExecutionUpdateRequest(BaseModel):
    """更新回归用例执行状态"""
    status: str = Field(..., description="执行状态: not_started/in_progress/passed/failed/blocked")
    executedBy: Optional[str] = Field(None, alias="executedBy")
    actualResult: Optional[str] = Field(None, alias="actualResult")
    comment: Optional[str] = Field(None)

    model_config = {"populate_by_name": True}


class ExecutionUpdateResponse(BaseModel):
    """更新回归用例执行状态响应"""
    id: str
    recommendationId: str = Field(alias="recommendationId")
    status: str
    executedBy: Optional[str] = Field(None, alias="executedBy")
    executedAt: Optional[datetime] = Field(None, alias="executedAt")
    actualResult: Optional[str] = Field(None, alias="actualResult")
    comment: Optional[str] = None

    model_config = {"populate_by_name": True}


class ModuleNode(BaseModel):
    """可视化模块节点"""
    id: str = Field(..., description="节点ID")
    name: str = Field(..., description="模块名称")
    moduleType: str = Field(..., alias="moduleType")
    riskLevel: str = Field(..., alias="riskLevel")
    isDirect: bool = Field(..., alias="isDirect", description="是否直接变更")
    changeFrequency: int = Field(default=0, alias="changeFrequency", description="历史变更频率")
    x: Optional[float] = Field(None, description="布局X坐标")
    y: Optional[float] = Field(None, description="布局Y坐标")


class ModuleEdge(BaseModel):
    """可视化模块关系边"""
    source: str = Field(..., description="源节点ID")
    target: str = Field(..., description="目标节点ID")
    relationType: str = Field(..., alias="relationType", description="关系类型: calls/depends_on/extends")
    weight: int = Field(default=1, description="关系权重")


class VisualizationData(BaseModel):
    """可视化数据结构"""
    nodes: list[ModuleNode] = Field(default_factory=list)
    edges: list[ModuleEdge] = Field(default_factory=list)
    summary: str = Field(..., description="可视化摘要")
    maxDepth: int = Field(default=3, alias="maxDepth", description="最大调用深度")
    totalNodes: int = Field(alias="totalNodes")
    totalEdges: int = Field(alias="totalEdges")
