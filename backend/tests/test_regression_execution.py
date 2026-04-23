"""测试 Sprint 5: /regression/recommendations/{id}/execute 执行状态追踪 API（TC-006 ~ TC-013）"""

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.main import app


def _seed_impact_analysis_and_recommendation() -> tuple[str, str]:
    """创建 ImpactAnalysis + RegressionRecommendation，返回 (analysis_id, recommendation_id)。"""
    from app.db.session import SessionLocal
    from app.models.impact import ImpactAnalysis, RegressionRecommendation

    db = SessionLocal()
    try:
        analysis = ImpactAnalysis(
            impact_summary="测试影响分析摘要",
            confidence_level="medium",
            status="completed",
        )
        db.add(analysis)
        db.flush()

        rec = RegressionRecommendation(
            analysis_id=analysis.id,
            priority="must",
            risk_level="high",
            reason="登录模块核心流程",
            estimated_minutes=10,
        )
        db.add(rec)
        db.commit()
        db.refresh(rec)
        return analysis.id, rec.id
    finally:
        db.close()


def _seed_impact_analysis_with_recommendations() -> tuple[str, list[str]]:
    """创建带多个推荐项的分析，返回 (analysis_id, [rec_id, ...])。"""
    from app.db.session import SessionLocal
    from app.models.impact import ImpactAnalysis, RegressionRecommendation

    db = SessionLocal()
    try:
        analysis = ImpactAnalysis(
            impact_summary="多推荐项测试",
            confidence_level="medium",
            status="completed",
        )
        db.add(analysis)
        db.flush()

        rec_ids = []
        for i in range(3):
            rec = RegressionRecommendation(
                analysis_id=analysis.id,
                priority="must" if i == 0 else "should",
                risk_level="high",
                reason=f"测试推荐 {i}",
                estimated_minutes=5,
            )
            db.add(rec)
            db.flush()
            rec_ids.append(rec.id)

        db.commit()
        return analysis.id, rec_ids
    finally:
        db.close()


def test_post_execute_creates_new_execution_record() -> None:
    """TC-006: POST 创建执行记录（无记录时）"""
    _, rec_id = _seed_impact_analysis_and_recommendation()
    try:
        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/regression/recommendations/{rec_id}/execute",
                json={"status": "passed"},
            )
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "passed"
        assert payload["recommendationId"] == rec_id
        assert payload["id"]
        assert payload["executedAt"] is not None

        # 验证数据库记录存在
        from app.db.session import SessionLocal
        from app.models.regression_execution import RegressionExecution

        db = SessionLocal()
        try:
            exec_record = db.query(RegressionExecution).filter_by(recommendation_id=rec_id).first()
            assert exec_record is not None
            assert exec_record.status == "passed"
        finally:
            db.close()
    finally:
        _cleanup_recommendation(rec_id)


def test_post_execute_updates_existing_record() -> None:
    """TC-007: POST 更新已有执行记录"""
    _, rec_id = _seed_impact_analysis_and_recommendation()
    try:
        # 第一次创建
        with TestClient(app) as client:
            r1 = client.post(
                f"/api/v1/regression/recommendations/{rec_id}/execute",
                json={"status": "in_progress", "executedBy": "tester-a"},
            )
            assert r1.status_code == 200
            first_execution_id = r1.json()["id"]
            first_executed_at = r1.json()["executedAt"]

        # 第二次更新
        with TestClient(app) as client:
            r2 = client.post(
                f"/api/v1/regression/recommendations/{rec_id}/execute",
                json={
                    "status": "failed",
                    "executedBy": "tester-b",
                    "actualResult": "界面显示异常",
                    "comment": "需要前端修复",
                },
            )
        assert r2.status_code == 200
        payload = r2.json()
        assert payload["status"] == "failed"
        assert payload["actualResult"] == "界面显示异常"
        assert payload["comment"] == "需要前端修复"
        assert payload["id"] == first_execution_id  # 同一记录
        # executedAt 应更新（时间戳不同）
        assert payload["executedAt"] != first_executed_at
    finally:
        _cleanup_recommendation(rec_id)


def test_get_execution_status_with_record() -> None:
    """TC-008: GET 获取执行状态（有记录）"""
    _, rec_id = _seed_impact_analysis_and_recommendation()
    try:
        # 先创建记录
        with TestClient(app) as client:
            client.post(
                f"/api/v1/regression/recommendations/{rec_id}/execute",
                json={
                    "status": "passed",
                    "executedBy": "zhangsan",
                    "actualResult": "全部通过",
                    "comment": "无问题",
                },
            )

        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/regression/recommendations/{rec_id}/execute",
            )
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "passed"
        assert payload["executedBy"] == "zhangsan"
        assert payload["actualResult"] == "全部通过"
        assert payload["comment"] == "无问题"
    finally:
        _cleanup_recommendation(rec_id)


def test_get_execution_status_without_record_returns_not_started() -> None:
    """TC-009: GET 获取执行状态（无记录）"""
    _, rec_id = _seed_impact_analysis_and_recommendation()
    try:
        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/regression/recommendations/{rec_id}/execute",
            )
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "not_started"
        assert payload["id"] == ""
        assert payload["recommendationId"] == rec_id
    finally:
        _cleanup_recommendation(rec_id)


def test_post_execute_invalid_status_returns_400() -> None:
    """TC-010: 无效 status 值返回 400"""
    _, rec_id = _seed_impact_analysis_and_recommendation()
    try:
        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/regression/recommendations/{rec_id}/execute",
                json={"status": "invalid_status"},
            )
        assert response.status_code == 400
        assert "无效的执行状态" in response.json()["detail"]
    finally:
        _cleanup_recommendation(rec_id)


def test_post_execute_nonexistent_recommendation_returns_404() -> None:
    """TC-011: 不存在的 recommendation_id 返回 404"""
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/regression/recommendations/nonexistent-id-12345/execute",
            json={"status": "passed"},
        )
    assert response.status_code == 404


def test_get_execution_nonexistent_recommendation_returns_404() -> None:
    """TC-011 (GET): 不存在的 recommendation_id GET 也返回 404"""
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/regression/recommendations/nonexistent-id-12345/execute",
        )
    assert response.status_code == 404


def test_all_five_status_values_accepted() -> None:
    """TC-012: 所有 5 种状态值均有效"""
    _, rec_id = _seed_impact_analysis_and_recommendation()
    try:
        statuses = ["not_started", "in_progress", "passed", "failed", "blocked"]
        with TestClient(app) as client:
            for s in statuses:
                response = client.post(
                    f"/api/v1/regression/recommendations/{rec_id}/execute",
                    json={"status": s},
                )
                assert response.status_code == 200, f"status={s} should be accepted"
                assert response.json()["status"] == s
    finally:
        _cleanup_recommendation(rec_id)


def test_execution_update_optional_fields_omitted() -> None:
    """TC-007 (补充): executedBy / actualResult / comment 均可选"""
    _, rec_id = _seed_impact_analysis_and_recommendation()
    try:
        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/regression/recommendations/{rec_id}/execute",
                json={"status": "blocked"},
            )
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "blocked"
        assert payload["executedBy"] is None
        assert payload["actualResult"] is None
        assert payload["comment"] is None
    finally:
        _cleanup_recommendation(rec_id)


def test_execution_update_with_all_fields() -> None:
    """TC-007 (补充): 完整字段更新"""
    _, rec_id = _seed_impact_analysis_and_recommendation()
    try:
        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/regression/recommendations/{rec_id}/execute",
                json={
                    "status": "failed",
                    "executedBy": "lisi",
                    "actualResult": "接口返回 500",
                    "comment": "后端 Bug，已提单 #1234",
                },
            )
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "failed"
        assert payload["executedBy"] == "lisi"
        assert payload["actualResult"] == "接口返回 500"
        assert payload["comment"] == "后端 Bug，已提单 #1234"
    finally:
        _cleanup_recommendation(rec_id)


def test_regression_recommendation_response_includes_execution_status() -> None:
    """TC-013: 回归推荐响应包含 executionStatus"""
    analysis_id, rec_ids = _seed_impact_analysis_with_recommendations()
    rec_id = rec_ids[0]
    try:
        # 为第一个推荐创建执行记录
        with TestClient(app) as client:
            client.post(
                f"/api/v1/regression/recommendations/{rec_id}/execute",
                json={"status": "passed"},
            )

        # 通过 GET /regression/recommendations/{analysis_id} 验证 executionStatus
        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/regression/recommendations/{analysis_id}",
            )
        assert response.status_code == 200
        payload = response.json()
        assert "mustRegress" in payload
        assert "shouldRegress" in payload

        # 找到带 execution record 的推荐项
        all_recs = payload["mustRegress"] + payload["shouldRegress"]
        target = next(r for r in all_recs if r["id"] == rec_id)
        assert target["executionStatus"] == "passed"

        # 其他推荐项无执行记录，应为 None
        others = [r for r in all_recs if r["id"] != rec_id]
        for r in others:
            assert r["executionStatus"] is None
    finally:
        for rid in rec_ids:
            _cleanup_recommendation(rid)


def test_impact_analysis_response_includes_execution_status() -> None:
    """TC-013 (补充): ImpactAnalysis 响应中 recommendations 也包含 executionStatus"""
    analysis_id, rec_ids = _seed_impact_analysis_with_recommendations()
    rec_id = rec_ids[0]
    try:
        # 创建执行记录
        with TestClient(app) as client:
            client.post(
                f"/api/v1/regression/recommendations/{rec_id}/execute",
                json={"status": "failed"},
            )

        # 通过 /impact-analysis/{id} 验证
        with TestClient(app) as client:
            response = client.get(f"/api/v1/impact-analysis/{analysis_id}")
        assert response.status_code == 200
        payload = response.json()
        assert "recommendations" in payload

        all_recs = payload["recommendations"]
        target = next(r for r in all_recs if r["id"] == rec_id)
        assert target["executionStatus"] == "failed"
    finally:
        for rid in rec_ids:
            _cleanup_recommendation(rid)


def _cleanup_recommendation(rec_id: str) -> None:
    """清理测试创建的推荐记录及关联执行记录（级联删除 execution）。"""
    from app.db.session import SessionLocal
    from app.models.impact import RegressionRecommendation

    db = SessionLocal()
    try:
        # 先清理孤立 execution 记录（父 RegressionRecommendation 被 cascade 删后会残留）
        db.execute(
            __import__("sqlalchemy").text(
                "DELETE FROM regression_executions WHERE recommendation_id = :rid"
            ),
            {"rid": rec_id},
        )
        rec = db.get(RegressionRecommendation, rec_id)
        if rec:
            db.delete(rec)
        db.commit()
    finally:
        db.close()
