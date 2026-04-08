from io import BytesIO

from fastapi.testclient import TestClient

from app.main import app


def test_create_and_list_knowledge_documents() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/knowledge/documents",
            json={
                "title": "登录模块历史缺陷",
                "docType": "defect",
                "moduleTags": ["登录", "认证"],
                "content": "缺陷1: 连续失败5次未锁定账户。缺陷2: 特殊字符密码无法登录。",
            },
        )
        assert response.status_code == 201
        doc = response.json()
        assert doc["title"] == "登录模块历史缺陷"
        assert doc["docType"] == "defect"
        assert doc["moduleTags"] == ["登录", "认证"]
        assert doc["status"] == "active"
        doc_id = doc["id"]

        list_response = client.get("/api/v1/knowledge/documents")
        assert list_response.status_code == 200
        items = list_response.json()["items"]
        assert any(item["id"] == doc_id for item in items)

        detail_response = client.get(f"/api/v1/knowledge/documents/{doc_id}")
        assert detail_response.status_code == 200
        detail = detail_response.json()
        assert detail["content"] == "缺陷1: 连续失败5次未锁定账户。缺陷2: 特殊字符密码无法登录。"

        client.delete(f"/api/v1/knowledge/documents/{doc_id}")


def test_update_knowledge_document() -> None:
    with TestClient(app) as client:
        create_resp = client.post(
            "/api/v1/knowledge/documents",
            json={"title": "测试文档", "content": "初始内容"},
        )
        doc_id = create_resp.json()["id"]

        update_resp = client.put(
            f"/api/v1/knowledge/documents/{doc_id}",
            json={"title": "更新后标题", "status": "deprecated"},
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["title"] == "更新后标题"
        assert update_resp.json()["status"] == "deprecated"

        client.delete(f"/api/v1/knowledge/documents/{doc_id}")


def test_delete_knowledge_document() -> None:
    with TestClient(app) as client:
        create_resp = client.post(
            "/api/v1/knowledge/documents",
            json={"title": "待删除", "content": "内容"},
        )
        doc_id = create_resp.json()["id"]

        delete_resp = client.delete(f"/api/v1/knowledge/documents/{doc_id}")
        assert delete_resp.status_code == 204

        get_resp = client.get(f"/api/v1/knowledge/documents/{doc_id}")
        assert get_resp.status_code == 404


def test_upload_knowledge_document() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/knowledge/documents/upload?docType=requirement",
            files=[
                ("file", ("req.txt", BytesIO("需求：用户可以登录系统".encode("utf-8")), "text/plain")),
            ],
        )
        assert response.status_code == 201
        doc = response.json()
        assert doc["sourceType"] == "upload"
        assert doc["sourceFilename"] == "req.txt"
        assert doc["docType"] == "requirement"

        client.delete(f"/api/v1/knowledge/documents/{doc['id']}")


def test_knowledge_stats() -> None:
    with TestClient(app) as client:
        resp = client.get("/api/v1/knowledge/stats")
        assert resp.status_code == 200
        stats = resp.json()
        assert "totalDocuments" in stats
        assert "activeDocuments" in stats
        assert "totalChunks" in stats


def test_reindex_knowledge_document() -> None:
    with TestClient(app) as client:
        create_resp = client.post(
            "/api/v1/knowledge/documents",
            json={"title": "索引测试", "content": "这是一段测试内容用于验证分块逻辑。"},
        )
        doc_id = create_resp.json()["id"]

        reindex_resp = client.post(f"/api/v1/knowledge/documents/{doc_id}/reindex")
        assert reindex_resp.status_code == 200

        detail = client.get(f"/api/v1/knowledge/documents/{doc_id}").json()
        assert detail["chunkCount"] >= 1
        assert len(detail["chunks"]) >= 1

        client.delete(f"/api/v1/knowledge/documents/{doc_id}")


def test_search_knowledge() -> None:
    with TestClient(app) as client:
        create_resp = client.post(
            "/api/v1/knowledge/documents",
            json={
                "title": "登录模块缺陷汇总",
                "docType": "defect",
                "moduleTags": ["登录模块"],
                "content": "连续登录失败后未锁定账户，属于高危缺陷。",
            },
        )
        doc_id = create_resp.json()["id"]

        search_resp = client.post(
            "/api/v1/knowledge/search",
            json={"query": "登录模块", "topK": 5},
        )
        assert search_resp.status_code == 200
        results = search_resp.json()["results"]
        assert any(r["documentId"] == doc_id for r in results)

        client.delete(f"/api/v1/knowledge/documents/{doc_id}")


def test_list_documents_with_filters() -> None:
    with TestClient(app) as client:
        client.post(
            "/api/v1/knowledge/documents",
            json={"title": "筛选测试A", "docType": "defect", "content": "内容A"},
        )
        client.post(
            "/api/v1/knowledge/documents",
            json={"title": "筛选测试B", "docType": "testcase", "content": "内容B"},
        )

        filtered = client.get("/api/v1/knowledge/documents?docType=defect")
        assert filtered.status_code == 200
        for item in filtered.json()["items"]:
            assert item["docType"] == "defect"
