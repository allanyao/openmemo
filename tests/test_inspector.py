import json
import pytest
from openmemo.api.rest_server import create_app


@pytest.fixture
def client(tmp_path):
    db_path = str(tmp_path / "test.db")
    app = create_app(db_path=db_path)
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def client_with_data(tmp_path):
    db_path = str(tmp_path / "test.db")
    app = create_app(db_path=db_path)
    app.config["TESTING"] = True
    with app.test_client() as c:
        c.post("/memory/write", json={
            "content": "User prefers Python",
            "scene": "coding",
            "type": "preference",
        })
        c.post("/memory/write", json={
            "content": "Deployed using Docker",
            "scene": "deployment",
            "type": "fact",
        })
        c.post("/memory/write", json={
            "content": "User uses pytest for testing",
            "scene": "coding",
            "type": "preference",
        })
        yield c


class TestInspectorPage:
    def test_inspector_returns_html(self, client):
        resp = client.get("/inspector")
        assert resp.status_code == 200
        assert resp.content_type.startswith("text/html")
        assert b"Memory Inspector" in resp.data


class TestInspectorChecklist:
    def test_checklist_returns_checks(self, client):
        resp = client.get("/api/inspector/checklist")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert "checks" in data
        assert len(data["checks"]) >= 4
        names = [c["name"] for c in data["checks"]]
        assert "Adapter Loaded" in names
        assert "Memory Backend Connected" in names

    def test_checklist_statuses(self, client):
        resp = client.get("/api/inspector/checklist")
        data = json.loads(resp.data)
        for check in data["checks"]:
            assert check["status"] in ("ok", "warning", "fail", "cold_start")


class TestInspectorMemorySummary:
    def test_empty_summary(self, client):
        resp = client.get("/api/inspector/memory-summary")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert "total_memories" in data
        assert "total_cells" in data
        assert "total_scenes" in data

    def test_summary_with_data(self, client_with_data):
        resp = client_with_data.get("/api/inspector/memory-summary")
        data = json.loads(resp.data)
        assert data["total_memories"] >= 3
        assert data["total_scenes"] >= 1


class TestInspectorRecent:
    def test_recent_empty(self, client):
        resp = client.get("/api/inspector/recent")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert "recent" in data

    def test_recent_with_data(self, client_with_data):
        resp = client_with_data.get("/api/inspector/recent")
        data = json.loads(resp.data)
        assert len(data["recent"]) >= 1

    def test_recent_limit(self, client_with_data):
        resp = client_with_data.get("/api/inspector/recent?limit=2")
        data = json.loads(resp.data)
        assert len(data["recent"]) <= 2


class TestInspectorSearch:
    def test_search_empty_query(self, client):
        resp = client.get("/api/inspector/search")
        data = json.loads(resp.data)
        assert data["results"] == []

    def test_search_with_results(self, client_with_data):
        resp = client_with_data.get("/api/inspector/search?q=Python")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert "results" in data

    def test_search_no_results(self, client_with_data):
        resp = client_with_data.get("/api/inspector/search?q=xyznonexistent")
        assert resp.status_code == 200


class TestInspectorHealth:
    def test_health(self, client):
        resp = client.get("/api/inspector/health")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["status"] == "ok"
        assert data["backend"] == "openmemo"
        assert "api_version" in data
        assert "total_memories" in data
