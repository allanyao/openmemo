"""Tests for OpenMemo MCP Transport Server."""
import io
import json
import pytest
from openmemo.api.sdk import Memory
from openmemo.adapters.mcp import OpenMemoMCPServer
from openmemo.adapters.mcp_server import (
    _handle_jsonrpc, _validate_jsonrpc, _read_message, _write_message,
)


@pytest.fixture
def mcp():
    mem = Memory(db_path=":memory:")
    return OpenMemoMCPServer(memory=mem, agent_id="test")


@pytest.fixture
def state():
    return {"done": True}


@pytest.fixture
def uninit_state():
    return {"done": False}


class TestValidation:
    def test_missing_jsonrpc(self, mcp, state):
        req = {"id": 1, "method": "ping"}
        resp = _handle_jsonrpc(req, mcp, state)
        assert resp["error"]["code"] == -32600

    def test_wrong_jsonrpc_version(self, mcp, state):
        req = {"jsonrpc": "1.0", "id": 1, "method": "ping"}
        resp = _handle_jsonrpc(req, mcp, state)
        assert resp["error"]["code"] == -32600

    def test_not_a_dict(self, mcp, state):
        resp = _handle_jsonrpc("not a dict", mcp, state)
        assert resp["error"]["code"] == -32600

    def test_validate_jsonrpc_valid(self):
        result = _validate_jsonrpc({"jsonrpc": "2.0", "method": "ping"})
        assert result is None


class TestInitialization:
    def test_initialize_response(self, mcp, uninit_state):
        req = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
        resp = _handle_jsonrpc(req, mcp, uninit_state)
        assert resp["id"] == 1
        result = resp["result"]
        assert result["protocolVersion"] == "2024-11-05"
        assert "tools" in result["capabilities"]
        assert result["serverInfo"]["name"] == "openmemo"
        assert uninit_state["done"] is True

    def test_initialized_notification(self, mcp, state):
        req = {"jsonrpc": "2.0", "method": "notifications/initialized"}
        resp = _handle_jsonrpc(req, mcp, state)
        assert resp is None

    def test_pre_initialize_gating(self, mcp, uninit_state):
        req = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
        resp = _handle_jsonrpc(req, mcp, uninit_state)
        assert resp["error"]["code"] == -32002

    def test_ping_before_initialize(self, mcp, uninit_state):
        req = {"jsonrpc": "2.0", "id": 1, "method": "ping"}
        resp = _handle_jsonrpc(req, mcp, uninit_state)
        assert resp["result"] == {}

    def test_notifications_before_initialize(self, mcp, uninit_state):
        req = {"jsonrpc": "2.0", "method": "notifications/something"}
        resp = _handle_jsonrpc(req, mcp, uninit_state)
        assert resp is None


class TestPing:
    def test_ping(self, mcp, state):
        req = {"jsonrpc": "2.0", "id": 2, "method": "ping"}
        resp = _handle_jsonrpc(req, mcp, state)
        assert resp["id"] == 2
        assert resp["result"] == {}


class TestToolsList:
    def test_list_tools(self, mcp, state):
        req = {"jsonrpc": "2.0", "id": 3, "method": "tools/list"}
        resp = _handle_jsonrpc(req, mcp, state)
        tools = resp["result"]["tools"]
        assert len(tools) == 4
        names = [t["name"] for t in tools]
        assert "write_memory" in names
        assert "recall_memory" in names
        assert "search_memory" in names
        assert "list_scenes" in names

    def test_tool_schema(self, mcp, state):
        req = {"jsonrpc": "2.0", "id": 4, "method": "tools/list"}
        resp = _handle_jsonrpc(req, mcp, state)
        write_tool = next(t for t in resp["result"]["tools"] if t["name"] == "write_memory")
        assert "inputSchema" in write_tool
        assert "content" in write_tool["inputSchema"]["properties"]


class TestToolsCall:
    def test_write_memory(self, mcp, state):
        req = {
            "jsonrpc": "2.0", "id": 5, "method": "tools/call",
            "params": {
                "name": "write_memory",
                "arguments": {"content": "User prefers Python", "scene": "coding"},
            },
        }
        resp = _handle_jsonrpc(req, mcp, state)
        assert resp["id"] == 5
        content = resp["result"]["content"]
        assert len(content) == 1
        assert content[0]["type"] == "text"
        data = json.loads(content[0]["text"])
        assert data["status"] == "stored"

    def test_recall_memory(self, mcp, state):
        _handle_jsonrpc({
            "jsonrpc": "2.0", "id": 10, "method": "tools/call",
            "params": {
                "name": "write_memory",
                "arguments": {"content": "Always use Docker for deployment"},
            },
        }, mcp, state)

        req = {
            "jsonrpc": "2.0", "id": 6, "method": "tools/call",
            "params": {
                "name": "recall_memory",
                "arguments": {"query": "Docker deployment"},
            },
        }
        resp = _handle_jsonrpc(req, mcp, state)
        content = resp["result"]["content"]
        data = json.loads(content[0]["text"])
        assert "context" in data

    def test_search_memory(self, mcp, state):
        _handle_jsonrpc({
            "jsonrpc": "2.0", "id": 10, "method": "tools/call",
            "params": {
                "name": "write_memory",
                "arguments": {"content": "Redis for caching layer"},
            },
        }, mcp, state)

        req = {
            "jsonrpc": "2.0", "id": 7, "method": "tools/call",
            "params": {
                "name": "search_memory",
                "arguments": {"query": "Redis"},
            },
        }
        resp = _handle_jsonrpc(req, mcp, state)
        data = json.loads(resp["result"]["content"][0]["text"])
        assert "results" in data

    def test_list_scenes(self, mcp, state):
        req = {
            "jsonrpc": "2.0", "id": 8, "method": "tools/call",
            "params": {
                "name": "list_scenes",
                "arguments": {},
            },
        }
        resp = _handle_jsonrpc(req, mcp, state)
        data = json.loads(resp["result"]["content"][0]["text"])
        assert "scenes" in data

    def test_unknown_tool_returns_error_flag(self, mcp, state):
        req = {
            "jsonrpc": "2.0", "id": 9, "method": "tools/call",
            "params": {
                "name": "nonexistent_tool",
                "arguments": {},
            },
        }
        resp = _handle_jsonrpc(req, mcp, state)
        data = json.loads(resp["result"]["content"][0]["text"])
        assert "error" in data
        assert resp["result"]["isError"] is True


class TestErrorHandling:
    def test_unknown_method(self, mcp, state):
        req = {"jsonrpc": "2.0", "id": 20, "method": "unknown/method"}
        resp = _handle_jsonrpc(req, mcp, state)
        assert resp["error"]["code"] == -32601

    def test_notification_unknown_method(self, mcp, state):
        req = {"jsonrpc": "2.0", "method": "notifications/unknown"}
        resp = _handle_jsonrpc(req, mcp, state)
        assert resp is None


class TestStdioFraming:
    def test_read_message(self):
        body = '{"jsonrpc":"2.0","id":1,"method":"ping"}'
        encoded = body.encode("utf-8")
        raw = f"Content-Length: {len(encoded)}\r\n\r\n{body}"
        stream = io.BytesIO(raw.encode("utf-8"))
        result = _read_message(stream)
        assert result == body
        parsed = json.loads(result)
        assert parsed["method"] == "ping"

    def test_write_message(self):
        output = io.StringIO()
        response = {"jsonrpc": "2.0", "id": 1, "result": {}}
        _write_message(output, response)
        written = output.getvalue()
        assert "Content-Length:" in written
        parts = written.split("\r\n\r\n", 1)
        assert len(parts) == 2
        header_line = parts[0]
        body = parts[1]
        assert json.loads(body) == response
        expected_len = len(body.encode("utf-8"))
        assert f"Content-Length: {expected_len}" in header_line

    def test_read_message_no_content_length(self):
        stream = io.BytesIO(b"\r\n")
        result = _read_message(stream)
        assert result is None

    def test_read_message_empty_stream(self):
        stream = io.BytesIO(b"")
        result = _read_message(stream)
        assert result is None

    def test_roundtrip(self):
        original = {"jsonrpc": "2.0", "id": 42, "result": {"tools": []}}
        output = io.StringIO()
        _write_message(output, original)
        written = output.getvalue()

        input_stream = io.BytesIO(written.encode("utf-8"))
        read_back = _read_message(input_stream)
        assert json.loads(read_back) == original


class TestFullWorkflow:
    def test_complete_mcp_session(self, mcp):
        state = {"done": False}

        init = _handle_jsonrpc(
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            mcp, state,
        )
        assert init["result"]["serverInfo"]["name"] == "openmemo"
        assert state["done"] is True

        _handle_jsonrpc(
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            mcp, state,
        )

        tools = _handle_jsonrpc(
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            mcp, state,
        )
        assert len(tools["result"]["tools"]) == 4

        write_resp = _handle_jsonrpc({
            "jsonrpc": "2.0", "id": 3, "method": "tools/call",
            "params": {
                "name": "write_memory",
                "arguments": {
                    "content": "Project uses PostgreSQL database",
                    "scene": "infrastructure",
                    "memory_type": "fact",
                },
            },
        }, mcp, state)
        data = json.loads(write_resp["result"]["content"][0]["text"])
        assert data["status"] == "stored"

        recall_resp = _handle_jsonrpc({
            "jsonrpc": "2.0", "id": 4, "method": "tools/call",
            "params": {
                "name": "recall_memory",
                "arguments": {"query": "database", "scene": "infrastructure"},
            },
        }, mcp, state)
        recall_data = json.loads(recall_resp["result"]["content"][0]["text"])
        assert "context" in recall_data

    def test_multiple_writes_and_search(self, mcp, state):
        for i, content in enumerate([
            "Python is the primary backend language",
            "React with TypeScript for frontend",
            "Deploy using Docker Compose",
        ]):
            _handle_jsonrpc({
                "jsonrpc": "2.0", "id": 100 + i, "method": "tools/call",
                "params": {"name": "write_memory", "arguments": {"content": content}},
            }, mcp, state)

        search_resp = _handle_jsonrpc({
            "jsonrpc": "2.0", "id": 200, "method": "tools/call",
            "params": {"name": "search_memory", "arguments": {"query": "technology stack"}},
        }, mcp, state)
        data = json.loads(search_resp["result"]["content"][0]["text"])
        assert "results" in data


class TestStreamableHTTP:
    @pytest.fixture(autouse=True)
    def setup_server(self):
        import threading
        import time
        from urllib.request import Request, urlopen
        from openmemo.adapters.mcp_server import _ThreadingHTTPServer, _StreamableHTTPHandler

        mem = Memory(db_path=":memory:")
        mcp_inst = OpenMemoMCPServer(memory=mem, agent_id="http_test")

        self.server = _ThreadingHTTPServer(("127.0.0.1", 0), _StreamableHTTPHandler)
        self.server._mcp = mcp_inst
        self.server._sessions = {}
        self.server._lock = threading.Lock()
        self.server._auth_token = ""
        self.port = self.server.server_address[1]
        self.base_url = f"http://127.0.0.1:{self.port}"

        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.daemon = True
        self.thread.start()
        time.sleep(0.1)

        yield

        self.server.shutdown()
        self.server.server_close()

    def _post(self, path, data, headers=None):
        from urllib.request import Request, urlopen
        body = json.dumps(data).encode()
        req = Request(f"{self.base_url}{path}", data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        if headers:
            for k, v in headers.items():
                req.add_header(k, v)
        with urlopen(req, timeout=5) as resp:
            resp_headers = dict(resp.headers)
            return json.loads(resp.read()), resp.status, resp_headers

    def _get(self, path):
        from urllib.request import Request, urlopen
        req = Request(f"{self.base_url}{path}")
        with urlopen(req, timeout=5) as resp:
            return json.loads(resp.read()), resp.status

    def test_health_check(self):
        data, status = self._get("/health")
        assert status == 200
        assert data["status"] == "ok"
        assert data["transport"] == "streamable-http"

    def test_initialize(self):
        data, status, headers = self._post("/mcp", {
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"capabilities": {}},
        })
        assert status == 200
        assert data["result"]["serverInfo"]["name"] == "openmemo"
        assert "Mcp-Session-Id" in headers

    def test_full_session(self):
        init_data, _, headers = self._post("/mcp", {
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"capabilities": {}},
        })
        session_id = headers.get("Mcp-Session-Id", "")
        assert session_id

        tools_data, _, _ = self._post("/mcp", {
            "jsonrpc": "2.0", "id": 2, "method": "tools/list",
        }, {"Mcp-Session-Id": session_id})
        assert len(tools_data["result"]["tools"]) == 4

        write_data, _, _ = self._post("/mcp", {
            "jsonrpc": "2.0", "id": 3, "method": "tools/call",
            "params": {
                "name": "write_memory",
                "arguments": {"content": "Streamable HTTP works great"},
            },
        }, {"Mcp-Session-Id": session_id})
        result = json.loads(write_data["result"]["content"][0]["text"])
        assert result["status"] == "stored"

        recall_data, _, _ = self._post("/mcp", {
            "jsonrpc": "2.0", "id": 4, "method": "tools/call",
            "params": {
                "name": "recall_memory",
                "arguments": {"query": "Streamable HTTP"},
            },
        }, {"Mcp-Session-Id": session_id})
        recall_result = json.loads(recall_data["result"]["content"][0]["text"])
        assert "context" in recall_result

    def test_wrong_content_type(self):
        from urllib.request import Request, urlopen
        from urllib.error import HTTPError
        req = Request(f"{self.base_url}/mcp", data=b'{}', method="POST")
        req.add_header("Content-Type", "text/plain")
        try:
            urlopen(req, timeout=5)
            assert False
        except HTTPError as e:
            assert e.code == 415

    def test_invalid_json(self):
        from urllib.request import Request, urlopen
        from urllib.error import HTTPError
        req = Request(f"{self.base_url}/mcp", data=b'not json', method="POST")
        req.add_header("Content-Type", "application/json")
        try:
            urlopen(req, timeout=5)
            assert False
        except HTTPError as e:
            assert e.code == 400

    def test_auth_required(self):
        import threading
        from urllib.request import Request, urlopen
        from urllib.error import HTTPError
        from openmemo.adapters.mcp_server import _ThreadingHTTPServer, _StreamableHTTPHandler

        auth_server = _ThreadingHTTPServer(("127.0.0.1", 0), _StreamableHTTPHandler)
        auth_server._mcp = self.server._mcp
        auth_server._sessions = {}
        auth_server._lock = threading.Lock()
        auth_server._auth_token = "test-secret-token"
        auth_port = auth_server.server_address[1]

        t = threading.Thread(target=auth_server.serve_forever)
        t.daemon = True
        t.start()

        try:
            req = Request(
                f"http://127.0.0.1:{auth_port}/mcp",
                data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}).encode(),
                method="POST",
            )
            req.add_header("Content-Type", "application/json")
            try:
                urlopen(req, timeout=5)
                assert False
            except HTTPError as e:
                assert e.code == 401

            req2 = Request(
                f"http://127.0.0.1:{auth_port}/mcp",
                data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}).encode(),
                method="POST",
            )
            req2.add_header("Content-Type", "application/json")
            req2.add_header("Authorization", "Bearer test-secret-token")
            with urlopen(req2, timeout=5) as resp:
                data = json.loads(resp.read())
                assert data["result"]["serverInfo"]["name"] == "openmemo"
        finally:
            auth_server.shutdown()
            auth_server.server_close()
