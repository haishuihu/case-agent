"""测试 Auto Test 模块 API"""

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.main import app


def _seed_test_suite(db, name="测试套件", description="测试描述"):
    """创建测试套件"""
    from app.models.auto_test import TestSuite
    suite = TestSuite(name=name, description=description)
    db.add(suite)
    db.commit()
    db.refresh(suite)
    return suite


def _seed_test_case(db, suite_id, title="测试用例", case_type="api"):
    """创建测试用例"""
    from app.models.auto_test import TestCase
    case = TestCase(
        suite_id=suite_id,
        title=title,
        case_type=case_type,
        method="GET",
        endpoint="/api/test",
        expected_status=200,
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


# ---- TestSuite API ----

def test_create_suite() -> None:
    """测试创建测试套件"""
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auto-test/suites",
            json={"name": "新建测试套件", "description": "这是一个测试套件"},
        )
    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "新建测试套件"
    assert payload["description"] == "这是一个测试套件"
    assert payload["id"]
    
    # 清理
    from app.db.session import SessionLocal
    from app.models.auto_test import TestSuite
    db = SessionLocal()
    try:
        db.query(TestSuite).filter(TestSuite.id == payload["id"]).delete()
        db.commit()
    finally:
        db.close()


def test_list_suites() -> None:
    """测试获取套件列表"""
    # 先创建一个套件
    from app.db.session import SessionLocal
    from app.models.auto_test import TestSuite
    db = SessionLocal()
    try:
        suite = _seed_test_suite(db, name="列表测试套件")
        
        with TestClient(app) as client:
            response = client.get("/api/v1/auto-test/suites")
        
        assert response.status_code == 200
        payload = response.json()
        assert isinstance(payload, list)
        
        # 清理
        db.delete(suite)
        db.commit()
    finally:
        db.close()


def test_get_suite() -> None:
    """测试获取单个套件"""
    from app.db.session import SessionLocal
    from app.models.auto_test import TestSuite
    db = SessionLocal()
    try:
        suite = _seed_test_suite(db, name="详情测试套件")
        
        with TestClient(app) as client:
            response = client.get(f"/api/v1/auto-test/suites/{suite.id}")
        
        assert response.status_code == 200
        payload = response.json()
        assert payload["id"] == suite.id
        assert payload["name"] == "详情测试套件"
        
        # 清理
        db.delete(suite)
        db.commit()
    finally:
        db.close()


def test_update_suite() -> None:
    """测试更新套件"""
    from app.db.session import SessionLocal
    from app.models.auto_test import TestSuite
    db = SessionLocal()
    try:
        suite = _seed_test_suite(db, name="更新前名称")
        
        with TestClient(app) as client:
            response = client.put(
                f"/api/v1/auto-test/suites/{suite.id}",
                json={"name": "更新后名称"},
            )
        
        assert response.status_code == 200
        payload = response.json()
        assert payload["name"] == "更新后名称"
        
        # 清理
        db.delete(suite)
        db.commit()
    finally:
        db.close()


def test_delete_suite() -> None:
    """测试删除套件"""
    from app.db.session import SessionLocal
    from app.models.auto_test import TestSuite
    db = SessionLocal()
    try:
        suite = _seed_test_suite(db, name="待删除套件")
        suite_id = suite.id
        
        with TestClient(app) as client:
            response = client.delete(f"/api/v1/auto-test/suites/{suite_id}")
        
        assert response.status_code == 200
        
        # 验证已删除
        with TestClient(app) as client:
            response = client.get(f"/api/v1/auto-test/suites/{suite_id}")
        assert response.status_code == 404
    finally:
        db.close()


# ---- TestCase API ----

def test_create_case() -> None:
    """测试创建用例"""
    from app.db.session import SessionLocal
    from app.models.auto_test import TestSuite
    db = SessionLocal()
    try:
        suite = _seed_test_suite(db, name="用例测试套件")
        
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/auto-test/cases",
                json={
                    "suite_id": suite.id,
                    "title": "测试用例标题",
                    "case_type": "api",
                    "method": "POST",
                    "endpoint": "/api/test",
                    "expected_status": 200,
                },
            )
        
        assert response.status_code == 200
        payload = response.json()
        assert payload["title"] == "测试用例标题"
        assert payload["case_type"] == "api"
        
        # 清理
        from app.models.auto_test import TestCase
        db.query(TestCase).filter(TestCase.id == payload["id"]).delete()
        db.delete(suite)
        db.commit()
    finally:
        db.close()


def test_list_cases() -> None:
    """测试获取用例列表"""
    from app.db.session import SessionLocal
    from app.models.auto_test import TestCase, TestSuite
    db = SessionLocal()
    try:
        suite = _seed_test_suite(db, name="用例列表测试套件")
        _seed_test_case(db, suite.id, title="列表用例1")
        _seed_test_case(db, suite.id, title="列表用例2")
        
        with TestClient(app) as client:
            response = client.get(f"/api/v1/auto-test/cases?suite_id={suite.id}")
        
        assert response.status_code == 200
        payload = response.json()
        assert isinstance(payload, list)
        assert len(payload) >= 2
        
        # 清理
        db.query(TestCase).filter(TestCase.suite_id == suite.id).delete()
        db.delete(suite)
        db.commit()
    finally:
        db.close()


def test_get_case() -> None:
    """测试获取单个用例"""
    from app.db.session import SessionLocal
    from app.models.auto_test import TestCase, TestSuite
    db = SessionLocal()
    try:
        suite = _seed_test_suite(db, name="用例详情测试套件")
        case = _seed_test_case(db, suite.id, title="详情测试用例")
        
        with TestClient(app) as client:
            response = client.get(f"/api/v1/auto-test/cases/{case.id}")
        
        assert response.status_code == 200
        payload = response.json()
        assert payload["id"] == case.id
        assert payload["title"] == "详情测试用例"
        
        # 清理
        db.delete(case)
        db.delete(suite)
        db.commit()
    finally:
        db.close()


def test_update_case() -> None:
    """测试更新用例"""
    from app.db.session import SessionLocal
    from app.models.auto_test import TestCase, TestSuite
    db = SessionLocal()
    try:
        suite = _seed_test_suite(db, name="用例更新测试套件")
        case = _seed_test_case(db, suite.id, title="更新前标题")
        
        with TestClient(app) as client:
            response = client.put(
                f"/api/v1/auto-test/cases/{case.id}",
                json={"title": "更新后标题", "priority": 1},
            )
        
        assert response.status_code == 200
        payload = response.json()
        assert payload["title"] == "更新后标题"
        
        # 清理
        db.delete(case)
        db.delete(suite)
        db.commit()
    finally:
        db.close()


def test_delete_case() -> None:
    """测试删除用例"""
    from app.db.session import SessionLocal
    from app.models.auto_test import TestCase, TestSuite
    db = SessionLocal()
    try:
        suite = _seed_test_suite(db, name="用例删除测试套件")
        case = _seed_test_case(db, suite.id, title="待删除用例")
        case_id = case.id
        
        with TestClient(app) as client:
            response = client.delete(f"/api/v1/auto-test/cases/{case_id}")
        
        assert response.status_code == 200
        
        # 验证已删除
        with TestClient(app) as client:
            response = client.get(f"/api/v1/auto-test/cases/{case_id}")
        assert response.status_code == 404
        
        # 清理
        db.delete(suite)
        db.commit()
    finally:
        db.close()


# ---- TestExecution API ----

def test_create_execution() -> None:
    """测试创建执行记录"""
    from app.db.session import SessionLocal
    from app.models.auto_test import TestSuite
    db = SessionLocal()
    try:
        suite = _seed_test_suite(db, name="执行测试套件")
        
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/auto-test/executions",
                json={
                    "suite_id": suite.id,
                    "name": "测试执行",
                    "triggered_by": "test",
                    "trigger_source": "manual",
                },
            )
        
        assert response.status_code == 200
        payload = response.json()
        assert payload["name"] == "测试执行"
        assert payload["status"] == "pending"
        
        # 清理
        from app.models.auto_test import TestExecution
        db.query(TestExecution).filter(TestExecution.id == payload["id"]).delete()
        db.delete(suite)
        db.commit()
    finally:
        db.close()


def test_list_executions() -> None:
    """测试获取执行列表"""
    from app.db.session import SessionLocal
    from app.models.auto_test import TestExecution, TestSuite
    db = SessionLocal()
    try:
        suite = _seed_test_suite(db, name="执行列表测试套件")
        
        # 创建执行记录
        execution = TestExecution(
            suite_id=suite.id,
            name="列表执行",
            status="completed",
            total_cases=10,
            passed_count=8,
            failed_count=2,
        )
        db.add(execution)
        db.commit()
        
        with TestClient(app) as client:
            response = client.get("/api/v1/auto-test/executions")
        
        assert response.status_code == 200
        payload = response.json()
        assert isinstance(payload, list)
        
        # 清理
        db.delete(execution)
        db.delete(suite)
        db.commit()
    finally:
        db.close()


def test_get_execution() -> None:
    """测试获取执行详情"""
    from app.db.session import SessionLocal
    from app.models.auto_test import TestExecution, TestSuite
    db = SessionLocal()
    try:
        suite = _seed_test_suite(db, name="执行详情测试套件")
        
        execution = TestExecution(
            suite_id=suite.id,
            name="详情执行",
            status="running",
        )
        db.add(execution)
        db.commit()
        db.refresh(execution)
        
        with TestClient(app) as client:
            response = client.get(f"/api/v1/auto-test/executions/{execution.id}")
        
        assert response.status_code == 200
        payload = response.json()
        assert payload["id"] == execution.id
        assert payload["name"] == "详情执行"
        
        # 清理
        db.delete(execution)
        db.delete(suite)
        db.commit()
    finally:
        db.close()


def test_start_execution() -> None:
    """测试启动执行"""
    from app.db.session import SessionLocal
    from app.models.auto_test import TestExecution, TestSuite
    db = SessionLocal()
    try:
        suite = _seed_test_suite(db, name="启动执行测试套件")
        
        execution = TestExecution(
            suite_id=suite.id,
            name="待启动执行",
            status="pending",
        )
        db.add(execution)
        db.commit()
        db.refresh(execution)
        
        with TestClient(app) as client:
            response = client.post(f"/api/v1/auto-test/executions/{execution.id}/start")
        
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "running"
        assert payload["started_at"] is not None
        
        # 清理
        db.delete(execution)
        db.delete(suite)
        db.commit()
    finally:
        db.close()


# ---- Dashboard API ----

def test_dashboard_stats() -> None:
    """测试仪表盘统计"""
    with TestClient(app) as client:
        response = client.get("/api/v1/auto-test/dashboard/stats")
    
    assert response.status_code == 200
    payload = response.json()
    assert "pending_count" in payload
    assert "running_count" in payload
    assert "today_pass_rate" in payload
    assert "total_suites" in payload
    assert "total_cases" in payload


def test_recent_executions() -> None:
    """测试最近执行记录"""
    with TestClient(app) as client:
        response = client.get("/api/v1/auto-test/dashboard/recent?limit=5")
    
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)


def test_execution_trends() -> None:
    """测试执行趋势"""
    with TestClient(app) as client:
        response = client.get("/api/v1/auto-test/dashboard/trends?days=7")
    
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)


# ---- Regression Recommend API ----

def test_regression_recommend() -> None:
    """测试回归推荐"""
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auto-test/recommend",
            json={
                "module_names": ["api", "user"],
                "max_cases": 10,
            },
        )
    
    assert response.status_code == 200
    payload = response.json()
    assert "total_recommended" in payload
    assert "recommendations" in payload
    assert "summary" in payload


# ---- TestPlan API ----

def test_create_plan() -> None:
    """测试创建测试计划"""
    from app.db.session import SessionLocal
    from app.models.auto_test import TestPlan, TestSuite
    db = SessionLocal()
    try:
        suite = _seed_test_suite(db, name="计划测试套件")
        
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/auto-test/plans",
                json={
                    "suite_id": suite.id,
                    "name": "测试计划",
                    "schedule_type": "manual",
                    "auto_execute": False,
                },
            )
        
        assert response.status_code == 200
        payload = response.json()
        assert payload["name"] == "测试计划"
        assert payload["schedule_type"] == "manual"
        
        # 清理
        db.query(TestPlan).filter(TestPlan.id == payload["id"]).delete()
        db.delete(suite)
        db.commit()
    finally:
        db.close()


def test_list_plans() -> None:
    """测试获取计划列表"""
    from app.db.session import SessionLocal
    from app.models.auto_test import TestPlan, TestSuite
    db = SessionLocal()
    try:
        suite = _seed_test_suite(db, name="计划列表测试套件")
        
        plan = TestPlan(
            suite_id=suite.id,
            name="列表测试计划",
            schedule_type="cron",
        )
        db.add(plan)
        db.commit()
        
        with TestClient(app) as client:
            response = client.get(f"/api/v1/auto-test/plans?suite_id={suite.id}")
        
        assert response.status_code == 200
        payload = response.json()
        assert isinstance(payload, list)
        
        # 清理
        db.delete(plan)
        db.delete(suite)
        db.commit()
    finally:
        db.close()


# ---- TestPlan Update/Delete ----

def test_update_plan() -> None:
    from app.db.session import SessionLocal
    from app.models.auto_test import TestPlan, TestSuite
    db = SessionLocal()
    try:
        suite = _seed_test_suite(db, name="更新计划测试套件")
        plan = TestPlan(suite_id=suite.id, name="原始计划", schedule_type="manual")
        db.add(plan)
        db.commit()
        db.refresh(plan)

        with TestClient(app) as client:
            response = client.put(
                f"/api/v1/auto-test/plans/{plan.id}",
                json={"name": "更新后的计划", "schedule_type": "cron"},
            )

        assert response.status_code == 200
        payload = response.json()
        assert payload["name"] == "更新后的计划"
        assert payload["schedule_type"] == "cron"

        db.delete(plan)
        db.delete(suite)
        db.commit()
    finally:
        db.close()


def test_delete_plan() -> None:
    from app.db.session import SessionLocal
    from app.models.auto_test import TestPlan, TestSuite
    db = SessionLocal()
    try:
        suite = _seed_test_suite(db, name="删除计划测试套件")
        plan = TestPlan(suite_id=suite.id, name="待删除计划")
        db.add(plan)
        db.commit()
        db.refresh(plan)

        with TestClient(app) as client:
            response = client.delete(f"/api/v1/auto-test/plans/{plan.id}")

        assert response.status_code == 200
        assert response.json()["message"] == "计划已删除"

        db.delete(suite)
        db.commit()
    finally:
        db.close()


# ---- TriggerConfig API ----

def test_create_trigger() -> None:
    from app.db.session import SessionLocal
    from app.models.auto_test import TestPlan, TestSuite
    db = SessionLocal()
    try:
        suite = _seed_test_suite(db, name="触发器测试套件")
        plan = TestPlan(suite_id=suite.id, name="触发器测试计划")
        db.add(plan)
        db.commit()
        db.refresh(plan)

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/auto-test/plans/{plan.id}/triggers",
                json={"trigger_type": "git_push", "name": "Git触发器", "enabled": True},
            )

        assert response.status_code == 200
        payload = response.json()
        assert payload["trigger_type"] == "git_push"
        assert payload["name"] == "Git触发器"
        assert payload["enabled"] is True

        # 清理: 级联删除会处理 trigger
        db.delete(plan)
        db.delete(suite)
        db.commit()
    finally:
        db.close()


def test_list_triggers() -> None:
    from app.db.session import SessionLocal
    from app.models.auto_test import TestPlan, TestSuite, TriggerConfig
    db = SessionLocal()
    try:
        suite = _seed_test_suite(db, name="触发器列表测试套件")
        plan = TestPlan(suite_id=suite.id, name="触发器列表计划")
        db.add(plan)
        db.commit()
        db.refresh(plan)

        trigger = TriggerConfig(plan_id=plan.id, trigger_type="schedule", name="定时触发器")
        db.add(trigger)
        db.commit()
        db.refresh(trigger)

        with TestClient(app) as client:
            response = client.get(f"/api/v1/auto-test/plans/{plan.id}/triggers")

        assert response.status_code == 200
        payload = response.json()
        assert isinstance(payload, list)

        db.delete(plan)
        db.delete(suite)
        db.commit()
    finally:
        db.close()


def test_update_trigger() -> None:
    from app.db.session import SessionLocal
    from app.models.auto_test import TestPlan, TestSuite, TriggerConfig
    db = SessionLocal()
    try:
        suite = _seed_test_suite(db, name="更新触发器测试套件")
        plan = TestPlan(suite_id=suite.id, name="更新触发器计划")
        db.add(plan)
        db.commit()
        db.refresh(plan)

        trigger = TriggerConfig(plan_id=plan.id, trigger_type="schedule", name="原始触发器")
        db.add(trigger)
        db.commit()
        db.refresh(trigger)

        with TestClient(app) as client:
            response = client.put(
                f"/api/v1/auto-test/triggers/{trigger.id}",
                json={"name": "更新后的触发器", "enabled": False},
            )

        assert response.status_code == 200
        payload = response.json()
        assert payload["name"] == "更新后的触发器"
        assert payload["enabled"] is False

        db.delete(plan)
        db.delete(suite)
        db.commit()
    finally:
        db.close()


def test_delete_trigger() -> None:
    from app.db.session import SessionLocal
    from app.models.auto_test import TestPlan, TestSuite, TriggerConfig
    db = SessionLocal()
    try:
        suite = _seed_test_suite(db, name="删除触发器测试套件")
        plan = TestPlan(suite_id=suite.id, name="删除触发器计划")
        db.add(plan)
        db.commit()
        db.refresh(plan)

        trigger = TriggerConfig(plan_id=plan.id, trigger_type="schedule", name="待删除触发器")
        db.add(trigger)
        db.commit()
        db.refresh(trigger)

        with TestClient(app) as client:
            response = client.delete(f"/api/v1/auto-test/triggers/{trigger.id}")

        assert response.status_code == 200
        assert response.json()["message"] == "触发器已删除"

        db.delete(plan)
        db.delete(suite)
        db.commit()
    finally:
        db.close()


# ---- Git Webhook ----

def test_git_webhook() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auto-test/webhooks/git",
            json={
                "event": "push",
                "branch": "main",
                "commit_sha": "abc123def456",
                "commit_message": "feat: add new feature",
                "changed_files": ["backend/app/api/routes/user.py"],
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["message"] == "Webhook received"
    assert "triggered_plans" in payload


# ---- Execution Update/Complete/Result ----

def test_update_execution() -> None:
    from app.db.session import SessionLocal
    from app.models.auto_test import TestExecution, TestSuite
    db = SessionLocal()
    try:
        suite = _seed_test_suite(db, name="更新执行测试套件")
        execution = TestExecution(suite_id=suite.id, name="待更新执行", status="pending")
        db.add(execution)
        db.commit()
        db.refresh(execution)

        with TestClient(app) as client:
            response = client.put(
                f"/api/v1/auto-test/executions/{execution.id}",
                json={"status": "running"},
            )

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "running"
        assert payload["started_at"] is not None

        db.delete(execution)
        db.delete(suite)
        db.commit()
    finally:
        db.close()


def test_complete_execution() -> None:
    from app.db.session import SessionLocal
    from app.models.auto_test import TestExecution, TestSuite
    db = SessionLocal()
    try:
        suite = _seed_test_suite(db, name="完成执行测试套件")
        execution = TestExecution(
            suite_id=suite.id,
            name="待完成执行",
            status="running",
            started_at=datetime.now(timezone.utc),
            passed_count=8,
            total_cases=10,
        )
        db.add(execution)
        db.commit()
        db.refresh(execution)

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/auto-test/executions/{execution.id}/complete?status=completed"
            )

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "completed"
        assert payload["pass_rate"] == 80.0
        assert payload["completed_at"] is not None

        db.delete(execution)
        db.delete(suite)
        db.commit()
    finally:
        db.close()


def test_create_result() -> None:
    from app.db.session import SessionLocal
    from app.models.auto_test import TestCase, TestExecution, TestSuite
    db = SessionLocal()
    try:
        suite = _seed_test_suite(db, name="结果测试套件")
        case = _seed_test_case(db, suite.id, title="结果测试用例")
        execution = TestExecution(suite_id=suite.id, name="结果测试执行", status="running")
        db.add(execution)
        db.commit()
        db.refresh(execution)

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/auto-test/executions/{execution.id}/results",
                json={
                    "case_id": case.id,
                    "result": "pass",
                    "response_status": 200,
                    "duration_ms": 150,
                },
            )

        assert response.status_code == 200
        payload = response.json()
        assert payload["result"] == "pass"
        assert payload["case_id"] == case.id

        db.delete(execution)
        db.delete(case)
        db.delete(suite)
        db.commit()
    finally:
        db.close()


# ---- Tags API ----

def test_create_tag() -> None:
    from app.db.session import SessionLocal
    from app.models.auto_test import TestCaseTag
    db = SessionLocal()
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/auto-test/tags",
                json={"name": "测试标签", "color": "#ff0000"},
            )

        assert response.status_code == 200
        payload = response.json()
        assert payload["name"] == "测试标签"
        assert payload["color"] == "#ff0000"

        db.query(TestCaseTag).filter(TestCaseTag.id == payload["id"]).delete()
        db.commit()
    finally:
        db.close()


def test_list_tags() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/auto-test/tags")

    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)


def test_delete_tag() -> None:
    from app.db.session import SessionLocal
    from app.models.auto_test import TestCaseTag
    db = SessionLocal()
    try:
        with TestClient(app) as client:
            create_resp = client.post(
                "/api/v1/auto-test/tags",
                json={"name": "待删除标签"},
            )

        tag_id = create_resp.json()["id"]

        with TestClient(app) as client:
            response = client.delete(f"/api/v1/auto-test/tags/{tag_id}")

        assert response.status_code == 200
        assert response.json()["message"] == "标签已删除"

        # verify deleted
        db2 = SessionLocal()
        try:
            tag = db2.query(TestCaseTag).filter(TestCaseTag.id == tag_id).first()
            assert tag is None
        finally:
            db2.close()
    finally:
        db.close()


# ---- Case Versions ----

def test_list_case_versions() -> None:
    from app.db.session import SessionLocal
    from app.models.auto_test import TestCaseVersion, TestSuite
    db = SessionLocal()
    try:
        suite = _seed_test_suite(db, name="版本测试套件")
        case = _seed_test_case(db, suite.id, title="版本测试用例")
        version = TestCaseVersion(
            case_id=case.id, version=1, content='{"title":"v1"}', change_summary="初始版本"
        )
        db.add(version)
        db.commit()

        with TestClient(app) as client:
            response = client.get(f"/api/v1/auto-test/cases/{case.id}/versions")

        assert response.status_code == 200
        payload = response.json()
        assert isinstance(payload, list)

        db.delete(version)
        db.delete(case)
        db.delete(suite)
        db.commit()
    finally:
        db.close()


# ---- Dashboard Failures ----

def test_dashboard_failures() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/auto-test/dashboard/failures?limit=5")

    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)


# ---- Case Clone ----

def test_clone_case() -> None:
    from app.db.session import SessionLocal
    from app.models.auto_test import TestSuite
    db = SessionLocal()
    try:
        suite = _seed_test_suite(db, name="克隆测试套件")
        case = _seed_test_case(db, suite.id, title="原始用例")

        with TestClient(app) as client:
            response = client.post(f"/api/v1/auto-test/cases/{case.id}/clone")

        assert response.status_code == 200
        payload = response.json()
        assert " (副本)" in payload["title"]
        assert payload["suite_id"] == suite.id
        assert payload["id"] != case.id

        # 清理克隆的用例
        from app.models.auto_test import TestCase
        db.query(TestCase).filter(TestCase.id == payload["id"]).delete()
        db.delete(case)
        db.delete(suite)
        db.commit()
    finally:
        db.close()


# ---- Retry Failed ----

def test_retry_failed() -> None:
    from app.db.session import SessionLocal
    from app.models.auto_test import TestCase, TestExecution, TestResult, TestSuite
    db = SessionLocal()
    try:
        suite = _seed_test_suite(db, name="重试测试套件")
        case = _seed_test_case(db, suite.id, title="重试测试用例")
        execution = TestExecution(
            suite_id=suite.id,
            name="重试测试执行",
            status="completed",
            passed_count=0,
            failed_count=1,
            total_cases=1,
        )
        db.add(execution)
        db.commit()
        db.refresh(execution)

        result = TestResult(
            execution_id=execution.id,
            case_id=case.id,
            result="fail",
            error_message="测试失败",
        )
        db.add(result)
        db.commit()

        with TestClient(app) as client:
            response = client.post(f"/api/v1/auto-test/executions/{execution.id}/retry-failed")

        assert response.status_code == 200
        payload = response.json()
        assert "重试" in payload["name"]
        assert payload["status"] == "pending"

        # 清理
        from app.models.auto_test import TestExecution as TE
        db.query(TE).filter(TE.id == payload["id"]).delete()
        db.delete(execution)
        db.delete(case)
        db.delete(suite)
        db.commit()
    finally:
        db.close()


# ---- Environment API ----

def test_create_environment() -> None:
    from app.db.session import SessionLocal
    from app.models.auto_test import TestEnvironment as Env
    db = SessionLocal()
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/auto-test/environments",
                json={"name": "测试环境", "base_url": "http://localhost:8000", "variables": {"KEY": "val"}},
            )

        assert response.status_code == 200
        payload = response.json()
        assert payload["name"] == "测试环境"
        assert payload["base_url"] == "http://localhost:8000"

        db.query(Env).filter(Env.id == payload["id"]).delete()
        db.commit()
    finally:
        db.close()


def test_list_environments() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/auto-test/environments")

    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)


def test_delete_environment() -> None:
    from app.db.session import SessionLocal
    from app.models.auto_test import TestEnvironment as Env
    db = SessionLocal()
    try:
        with TestClient(app) as client:
            create_resp = client.post(
                "/api/v1/auto-test/environments",
                json={"name": "待删除环境"},
            )
        env_id = create_resp.json()["id"]

        with TestClient(app) as client:
            response = client.delete(f"/api/v1/auto-test/environments/{env_id}")

        assert response.status_code == 200
        assert response.json()["message"] == "环境已删除"
    finally:
        db.close()
