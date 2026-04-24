"""测试缺陷管理 API（/api/v1/defects）"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _create_one(
    title: str = "登录按钮点击无响应",
    severity: str = "high",
    priority: str = "medium",
    extra: dict | None = None,
) -> dict:
    payload = {"title": title, "severity": severity, "priority": priority}
    if extra:
        payload.update(extra)
    resp = client.post("/api/v1/defects", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


class TestCreateDefect:
    def test_create_defect_required_fields(self) -> None:
        """TC-001: 仅必填字段创建缺陷"""
        d = _create_one()
        assert d["title"] == "登录按钮点击无响应"
        assert d["severity"] == "high"
        assert d["priority"] == "medium"
        assert d["status"] == "open"
        assert "id" in d
        assert "createdAt" in d

    def test_create_defect_all_fields(self) -> None:
        """TC-002: 填写全部字段"""
        d = _create_one(
            title="支付页面空白",
            severity="critical",
            priority="high",
            extra={
                "description": "选择支付方式后页面变空白",
                "environment": "Android 14 / Chrome 120",
                "browser": "Chrome",
                "creator": "张三",
                "assignee": "李四",
            },
        )
        assert d["description"] == "选择支付方式后页面变空白"
        assert d["environment"] == "Android 14 / Chrome 120"
        assert d["browser"] == "Chrome"
        assert d["creator"] == "张三"
        assert d["assignee"] == "李四"

    def test_create_defect_invalid_severity(self) -> None:
        """TC-003: 无效的严重程度返回 400"""
        resp = client.post("/api/v1/defects", json={"title": "测试", "severity": "blocker"})
        assert resp.status_code == 400
        assert "无效的严重程度" in resp.json()["detail"]

    def test_create_defect_missing_title(self) -> None:
        """TC-004: 缺少必填字段 title 返回 422"""
        resp = client.post("/api/v1/defects", json={"severity": "high"})
        assert resp.status_code == 422


class TestListDefects:
    def test_list_defects_empty(self) -> None:
        """TC-005: 空列表返回空数组"""
        resp = client.get("/api/v1/defects")
        assert resp.status_code == 200
        payload = resp.json()
        assert "items" in payload
        assert "total" in payload

    def test_list_defects_pagination(self) -> None:
        """TC-006: 分页参数生效"""
        _create_one(title="缺陷A")
        _create_one(title="缺陷B")
        resp = client.get("/api/v1/defects?page=1&pageSize=1")
        assert resp.status_code == 200
        payload = resp.json()
        assert len(payload["items"]) == 1
        assert payload["total"] >= 2
        assert payload["page"] == 1
        assert payload["pageSize"] == 1

    def test_list_defects_filter_by_status(self) -> None:
        """TC-007: 按状态筛选"""
        d1 = _create_one(title="待处理缺陷")
        d2 = _create_one(title="另一个缺陷")
        # 将 d2 状态改为 resolved
        client.patch(f'/api/v1/defects/{d2["id"]}', json={"status": "resolved"})

        resp = client.get("/api/v1/defects?status=open")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert all(item["status"] == "open" for item in items)

    def test_list_defects_filter_by_severity(self) -> None:
        """TC-008: 按严重程度筛选"""
        _create_one(title="高严重缺陷", severity="high")
        _create_one(title="低严重缺陷", severity="low")

        resp = client.get("/api/v1/defects?severity=high")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert all(item["severity"] == "high" for item in items)

    def test_list_defects_invalid_status(self) -> None:
        """TC-009: 无效状态值返回 400"""
        resp = client.get("/api/v1/defects?status=unknown")
        assert resp.status_code == 400
        assert "无效的状态值" in resp.json()["detail"]

    def test_list_defects_invalid_severity(self) -> None:
        """TC-010: 无效严重程度值返回 400"""
        resp = client.get("/api/v1/defects?severity=blocker")
        assert resp.status_code == 400
        assert "无效的严重程度" in resp.json()["detail"]


class TestGetDefect:
    def test_get_defect(self) -> None:
        """TC-011: 获取已存在的缺陷"""
        d = _create_one(title="详情测试缺陷")
        resp = client.get(f'/api/v1/defects/{d["id"]}')
        assert resp.status_code == 200
        assert resp.json()["title"] == "详情测试缺陷"

    def test_get_defect_not_found(self) -> None:
        """TC-012: 获取不存在的缺陷返回 404"""
        resp = client.get("/api/v1/defects/nonexistent-id-12345")
        assert resp.status_code == 404


class TestUpdateDefect:
    def test_update_defect_status(self) -> None:
        """TC-013: 更新状态"""
        d = _create_one()
        resp = client.patch(f'/api/v1/defects/{d["id"]}', json={"status": "in_progress"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "in_progress"

    def test_update_defect_resolved_sets_resolved_at(self) -> None:
        """TC-014: 标记为已解决时 resolvedAt 被设置"""
        d = _create_one()
        resp = client.patch(f'/api/v1/defects/{d["id"]}', json={"status": "resolved"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "resolved"
        assert resp.json().get("resolvedAt") is not None

    def test_update_defect_invalid_status(self) -> None:
        """TC-015: 更新为无效状态返回 400"""
        d = _create_one()
        resp = client.patch(f'/api/v1/defects/{d["id"]}', json={"status": "done"})
        assert resp.status_code == 400

    def test_update_defect_not_found(self) -> None:
        """TC-016: 更新不存在的缺陷返回 404"""
        resp = client.patch("/api/v1/defects/nonexistent-id-12345", json={"status": "resolved"})
        assert resp.status_code == 404


class TestDeleteDefect:
    def test_delete_defect(self) -> None:
        """TC-017: 删除缺陷"""
        d = _create_one(title="待删除缺陷")
        resp = client.delete(f'/api/v1/defects/{d["id"]}')
        assert resp.status_code == 204

        # 确认已删除
        get_resp = client.get(f'/api/v1/defects/{d["id"]}')
        assert get_resp.status_code == 404

    def test_delete_defect_not_found(self) -> None:
        """TC-018: 删除不存在的缺陷返回 404"""
        resp = client.delete("/api/v1/defects/nonexistent-id-12345")
        assert resp.status_code == 404
