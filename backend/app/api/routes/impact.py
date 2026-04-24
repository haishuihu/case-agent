from __future__ import annotations

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.models.impact import ImpactAnalysis, ImpactedModule
from app.models.submission import Submission
from app.schemas.impact import (
    ImpactAnalysisRequest,
    ImpactAnalysisResponse,
    ChangedFileItem,
    ImpactedModuleResponse,
    RegressionRecommendationResponse,
    VisualizationData,
    ModuleNode,
    ModuleEdge,
)
from app.services.impact_analyzer import ImpactAnalyzer
from app.services.regression_recommender import RegressionRecommender

router = APIRouter(prefix="/impact-analysis", tags=["impact-analysis"])
logger = logging.getLogger(__name__)


def _serialize_modules(modules: Optional[list]) -> Optional[str]:
    if modules is None:
        return None
    return json.dumps(modules, ensure_ascii=False)


def _deserialize_modules(raw: Optional[str]) -> list:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def _build_response(analysis: ImpactAnalysis) -> ImpactAnalysisResponse:
    """将 ORM 模型转换为响应 schema"""
    impacted_modules = [
        ImpactedModuleResponse(
            id=m.id,
            moduleName=m.module_name,
            moduleType=m.module_type,
            riskLevel=m.risk_level,
            impactDescription=m.impact_description or "",
        )
        for m in analysis.impacted_modules
    ]

    changed_files = _deserialize_modules(analysis.changed_files)
    changed_file_items = [
        ChangedFileItem(
            filename=f.get("filename", ""),
            status=f.get("status", "modified"),
            additions=f.get("additions", 0),
            deletions=f.get("deletions", 0),
        )
        for f in changed_files
    ]

    modified_functions = _deserialize_modules(analysis.modified_functions)

    recommendations = [
        RegressionRecommendationResponse(
            id=r.id,
            caseId=r.case_id or None,
            caseTitle=r.case_title or None,
            priority=r.priority,
            riskLevel=r.risk_level,
            reason=r.reason or None,
            estimatedMinutes=r.estimated_minutes,
            category=r.category,
            executionStatus=r.execution.status if r.execution else None,
        )
        for r in analysis.recommendations
    ]

    total_minutes = sum(r.estimated_minutes or 0 for r in analysis.recommendations)

    return ImpactAnalysisResponse(
        id=analysis.id,
        submissionId=analysis.submission_id,
        changedFiles=changed_file_items,
        addedLines=analysis.added_lines,
        deletedLines=analysis.deleted_lines,
        modifiedFunctions=modified_functions,
        impactedModules=impacted_modules,
        indirectImpacts=[],
        apiBreakingChanges=[],
        riskPoints=[],
        confidenceLevel=analysis.confidence_level,
        summary=analysis.impact_summary or "",
        recommendations=recommendations,
        estimatedTotalMinutes=total_minutes,
        createdAt=analysis.created_at,
    )


@router.post("", response_model=ImpactAnalysisResponse, status_code=status.HTTP_201_CREATED)
def create_impact_analysis(
    request: ImpactAnalysisRequest,
    db: Session = Depends(get_db_session),
) -> ImpactAnalysisResponse:
    """
    创建一条影响分析记录（同时执行分析）

    输入 Git Diff，返回完整的影响分析报告和回归推荐。
    """
    # 验证 submission_id 存在（如有提供）
    if request.submissionId:
        submission = db.get(Submission, request.submissionId)
        if not submission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"提测申请 {request.submissionId} 不存在",
            )

    # 执行分析
    analyzer = ImpactAnalyzer()
    result = analyzer.analyze(
        git_diff=request.gitDiff,
        affected_modules=request.affectedModules,
        submission_id=request.submissionId,
        recent_defects=request.recentDefects,
    )

    # 保存分析记录
    analysis = ImpactAnalysis(
        submission_id=request.submissionId,
        git_diff=request.gitDiff,
        changed_files=_serialize_modules(result["changed_files"]),
        added_lines=result["added_lines"],
        deleted_lines=result["deleted_lines"],
        modified_functions=_serialize_modules(result["modified_functions"]),
        impact_summary=result["summary"],
        confidence_level=result["confidence_level"],
        status="completed",
    )
    db.add(analysis)
    db.flush()

    # 保存受影响模块
    for m in result["impacted_modules"]:
        db.add(ImpactedModule(
            analysis_id=analysis.id,
            module_name=m["module_name"],
            module_type=m.get("module_type", "direct"),
            risk_level=m.get("risk_level", "medium"),
            impact_description=m.get("impact_description"),
        ))

    # 执行回归推荐并保存
    recommender = RegressionRecommender()
    recs = recommender.recommend(
        impacted_modules=result["impacted_modules"],
        summary=result["summary"],
        recent_defects=request.recentDefects,
    )

    from app.models.impact import RegressionRecommendation

    for rec in recs:
        db.add(RegressionRecommendation(
            analysis_id=analysis.id,
            case_id=rec.get("case_id"),
            case_title=rec.get("case_title"),
            priority=rec.get("priority", "should"),
            risk_level=rec.get("risk_level", "medium"),
            reason=rec.get("reason"),
            estimated_minutes=rec.get("estimated_minutes"),
            category=rec.get("category"),
        ))

    db.commit()
    db.refresh(analysis)

    logger.info("[impact] created analysis id=%s", analysis.id)
    return _build_response(analysis)


@router.get("/submissions/{submission_id}", response_model=ImpactAnalysisResponse)
def get_latest_impact(
    submission_id: str,
    db: Session = Depends(get_db_session),
) -> ImpactAnalysisResponse:
    """获取指定提测的最新一条影响分析"""
    analysis = (
        db.query(ImpactAnalysis)
        .filter(ImpactAnalysis.submission_id == submission_id)
        .order_by(ImpactAnalysis.created_at.desc())
        .first()
    )
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"提测 {submission_id} 暂无影响分析记录",
        )
    return _build_response(analysis)


@router.get("/{analysis_id}", response_model=ImpactAnalysisResponse)
def get_impact_analysis(
    analysis_id: str,
    db: Session = Depends(get_db_session),
) -> ImpactAnalysisResponse:
    """根据 ID 获取影响分析详情"""
    analysis = db.get(ImpactAnalysis, analysis_id)
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"影响分析 {analysis_id} 不存在",
        )
    return _build_response(analysis)


@router.get("/{analysis_id}/visualization", response_model=VisualizationData)
def get_impact_visualization(
    analysis_id: str,
    db: Session = Depends(get_db_session),
) -> VisualizationData:
    """获取影响分析的可视化数据（模块关系图）"""
    analysis = db.get(ImpactAnalysis, analysis_id)
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"影响分析 {analysis_id} 不存在",
        )

    nodes: list[ModuleNode] = []
    edges: list[ModuleEdge] = []
    node_ids: set[str] = set()

    # 为每个受影响模块创建节点
    import json as _json

    changed_files: list[dict] = []
    if analysis.changed_files:
        try:
            changed_files = _json.loads(analysis.changed_files)
        except _json.JSONDecodeError:
            pass

    # 直接变更的模块
    changed_modules_set: set[str] = set()
    for f in changed_files:
        fname = f.get("filename", "")
        if fname:
            parts = fname.split("/")
            if len(parts) >= 2:
                module_name = parts[-2]
            else:
                module_name = parts[-1]
            changed_modules_set.add(module_name)

    for i, module in enumerate(analysis.impacted_modules):
        node_id = f"node_{i}"
        node_ids.add(node_id)

        # 圆形布局
        import math
        angle = 2 * math.pi * i / max(len(analysis.impacted_modules), 1)
        radius = 200

        nodes.append(ModuleNode(
            id=node_id,
            name=module.module_name,
            moduleType=module.module_type,
            riskLevel=module.risk_level,
            isDirect=module.module_type == "direct",
            changeFrequency=1 if module.module_type == "direct" else 0,
            x=300 + radius * math.cos(angle),
            y=300 + radius * math.sin(angle),
        ))

        # 创建从变更模块到受影响模块的边
        for j, changed_mod in enumerate(changed_modules_set):
            if module.module_type == "direct":
                continue
            edge_id = f"edge_{i}_{j}"
            edges.append(ModuleEdge(
                source=f"changed_{j}",
                target=node_id,
                relationType="calls",
                weight=1 if module.risk_level == "high" else 1,
            ))

    # 添加变更模块节点（中心）
    center_x = 300.0
    center_y = 300.0
    changed_nodes = []
    for j, mod in enumerate(sorted(changed_modules_set)):
        node_id = f"changed_{j}"
        nodes.append(ModuleNode(
            id=node_id,
            name=mod,
            moduleType="direct",
            riskLevel="high",
            isDirect=True,
            changeFrequency=1,
            x=center_x,
            y=center_y,
        ))
        changed_nodes.append(node_id)

    # 添加从变更模块到直接受影响模块的边
    for module in analysis.impacted_modules:
        if module.module_type == "direct":
            for changed_idx, mod in enumerate(sorted(changed_modules_set)):
                edges.append(ModuleEdge(
                    source=f"changed_{changed_idx}",
                    target=next((n.id for n in nodes if n.name == module.module_name), ""),
                    relationType="calls",
                    weight=2,
                ))

    summary = (
        f"共 {len(nodes)} 个模块节点，{len(edges)} 条关系边。"
        f"变更涉及 {len(changed_modules_set)} 个直接模块，"
        f"影响 {len(analysis.impacted_modules)} 个模块。"
    )

    return VisualizationData(
        nodes=nodes,
        edges=edges,
        summary=summary,
        maxDepth=3,
        totalNodes=len(nodes),
        totalEdges=len(edges),
    )
