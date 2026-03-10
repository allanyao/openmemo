"""
MCP Transport Server for OpenMemo.

Implements the Model Context Protocol (JSON-RPC 2.0) transport layer,
wrapping OpenMemoMCPServer with stdio and SSE transports.

Supports all MCP-compatible clients:
- Claude Desktop, Claude Code, claude.ai (Remote MCP)
- VS Code, Cursor, Windsurf, JetBrains, Zed, Kilo Code
- Gemini CLI, Gemini Code Assist, OpenCode, Codex CLI
- Goose, Aider, GitHub Copilot CLI, Amp, Continue
- Replit, Sourcegraph, Qodo, Raycast
- ChatGPT (Developer Mode)

Usage (stdio):
    openmemo mcp serve
    python -m openmemo.adapters.mcp_server

Usage (SSE):
    openmemo mcp serve --transport sse --port 8780

Client config (claude_desktop_config.json / mcp.json):
    {
        "mcpServers": {
            "openmemo": {
                "command": "openmemo",
                "args": ["mcp", "serve"],
                "env": {
                    "OPENMEMO_DB": "openmemo.db"
                }
            }
        }
    }
"""

import json
import logging
import os
import sys
import threading
import uuid
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

logger = logging.getLogger("openmemo.mcp")

SERVER_NAME = "openmemo"
SERVER_VERSION = "0.7.0"
PROTOCOL_VERSION = "2024-11-05"


def _build_mcp_server(db_path, agent_id):
    from openmemo.adapters.mcp import OpenMemoMCPServer
    return OpenMemoMCPServer(db_path=db_path, agent_id=agent_id)


def _validate_jsonrpc(request) -> dict:
    if not isinstance(request, dict):
        return {"code": -32600, "message": "Invalid Request: not an object"}
    if request.get("jsonrpc") != "2.0":
        return {"code": -32600, "message": "Invalid Request: missing jsonrpc 2.0"}
    if "method" not in request:
        if "id" in request:
            return {"code": -32600, "message": "Invalid Request: missing method"}
    return None


def _handle_jsonrpc(request, mcp, initialized: dict) -> dict:
    validation_error = _validate_jsonrpc(request)
    if validation_error:
        return {
            "jsonrpc": "2.0",
            "id": request.get("id") if isinstance(request, dict) else None,
            "error": validation_error,
        }

    method = request.get("method", "")
    req_id = request.get("id")
    params = request.get("params", {})

    if method == "initialize":
        initialized["done"] = True
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {
                    "tools": {"listChanged": False},
                },
                "serverInfo": {
                    "name": SERVER_NAME,
                    "version": SERVER_VERSION,
                },
            },
        }

    if method.startswith("notifications/"):
        return None

    if method == "ping":
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}

    if not initialized.get("done") and req_id is not None:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {
                "code": -32002,
                "message": "Server not initialized. Send initialize first.",
            },
        }

    if method == "tools/list":
        tools = mcp.get_tools()
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": tools},
        }

    if method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        try:
            result = mcp.handle_tool(tool_name, arguments)
            is_error = "error" in result
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {"type": "text", "text": json.dumps(result, ensure_ascii=False)},
                    ],
                    **({"isError": True} if is_error else {}),
                },
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {"type": "text", "text": json.dumps({"error": str(e)})},
                    ],
                    "isError": True,
                },
            }

    if req_id is not None:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {
                "code": -32601,
                "message": f"Method not found: {method}",
            },
        }

    return None


def _read_message(input_stream) -> str:
    headers = {}
    while True:
        line = input_stream.readline()
        if isinstance(line, bytes):
            line = line.decode("utf-8")
        if not line:
            return None
        line = line.strip()
        if line == "":
            if headers:
                break
            continue
        if ":" in line:
            key, value = line.split(":", 1)
            headers[key.strip().lower()] = value.strip()

    content_length = int(headers.get("content-length", 0))
    if content_length <= 0:
        return None

    data = input_stream.read(content_length)
    if isinstance(data, bytes):
        data = data.decode("utf-8")
    return data


def _write_message(output_stream, response: dict):
    body = json.dumps(response, ensure_ascii=False)
    encoded = body.encode("utf-8")
    header = f"Content-Length: {len(encoded)}\r\n\r\n"
    output_stream.write(header)
    output_stream.write(body)
    output_stream.flush()


def run_stdio(db_path: str = "openmemo.db", agent_id: str = ""):
    mcp = _build_mcp_server(db_path, agent_id)
    initialized = {"done": False}

    logger.info("OpenMemo MCP server starting (stdio)")

    stdin = sys.stdin
    stdout = sys.stdout

    if hasattr(stdin, 'buffer'):
        stdin_bin = stdin.buffer
    else:
        stdin_bin = stdin

    while True:
        try:
            raw = _read_message(stdin_bin)
            if raw is None:
                break

            try:
                request = json.loads(raw)
            except json.JSONDecodeError:
                error_resp = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": "Parse error"},
                }
                _write_message(stdout, error_resp)
                continue

            response = _handle_jsonrpc(request, mcp, initialized)

            if response is not None:
                _write_message(stdout, response)

        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error("MCP stdio error: %s", e)
            break

    mcp.close()


class _ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


class _SSEHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        logger.debug("SSE HTTP: %s", format % args)

    def _check_auth(self) -> bool:
        token = self.server._auth_token
        if not token:
            return True
        auth_header = self.headers.get("Authorization", "")
        if auth_header == f"Bearer {token}":
            return True
        self._respond_json(401, {"error": "unauthorized"})
        return False

    def do_GET(self):
        if self.path == "/sse":
            if not self._check_auth():
                return
            self._handle_sse()
        elif self.path == "/health":
            self._respond_json(200, {"status": "ok", "server": SERVER_NAME, "version": SERVER_VERSION})
        else:
            self._respond_json(404, {"error": "not found"})

    def do_POST(self):
        if self.path.startswith("/message"):
            if not self._check_auth():
                return
            self._handle_message()
        else:
            self._respond_json(404, {"error": "not found"})

    def _handle_sse(self):
        session_id = str(uuid.uuid4())
        session_data = {"initialized": {"done": False}}

        with self.server._lock:
            self.server._sessions[session_id] = session_data
            self.server._sse_connections[session_id] = self

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        endpoint_event = f"event: endpoint\ndata: /message?sessionId={session_id}\n\n"
        self.wfile.write(endpoint_event.encode())
        self.wfile.flush()

        logger.info("SSE client connected: %s", session_id)

        stop_event = threading.Event()
        session_data["stop_event"] = stop_event

        try:
            while not stop_event.is_set():
                stop_event.wait(30)
                if not stop_event.is_set():
                    try:
                        self.wfile.write(b": keepalive\n\n")
                        self.wfile.flush()
                    except (BrokenPipeError, ConnectionResetError, OSError):
                        break
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            with self.server._lock:
                self.server._sse_connections.pop(session_id, None)
                self.server._sessions.pop(session_id, None)
            logger.info("SSE client disconnected: %s", session_id)

    def _handle_message(self):
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        session_id = qs.get("sessionId", [None])[0]

        with self.server._lock:
            session = self.server._sessions.get(session_id)

        if not session_id or not session:
            self._respond_json(400, {"error": "invalid session"})
            return

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)

        try:
            request = json.loads(body)
        except json.JSONDecodeError:
            self._respond_json(400, {"error": "invalid JSON"})
            return

        response = _handle_jsonrpc(request, self.server._mcp, session.get("initialized", {"done": False}))

        self.send_response(202)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(b'{"status":"accepted"}')
        self.wfile.flush()

        if response is not None:
            with self.server._lock:
                sse_conn = self.server._sse_connections.get(session_id)
            if sse_conn:
                try:
                    event_data = json.dumps(response, ensure_ascii=False)
                    sse_msg = f"event: message\ndata: {event_data}\n\n"
                    sse_conn.wfile.write(sse_msg.encode())
                    sse_conn.wfile.flush()
                except (BrokenPipeError, OSError) as e:
                    logger.warning("Failed to send SSE response: %s", e)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def _respond_json(self, status, data):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run_sse(host: str = "127.0.0.1", port: int = 8780,
            db_path: str = "openmemo.db", agent_id: str = "",
            auth_token: str = None):
    mcp = _build_mcp_server(db_path, agent_id)

    server = _ThreadingHTTPServer((host, port), _SSEHandler)
    server._mcp = mcp
    server._sessions = {}
    server._sse_connections = {}
    server._lock = threading.Lock()
    server._auth_token = auth_token or os.environ.get("OPENMEMO_MCP_TOKEN", "")

    print(f"OpenMemo MCP Server (SSE) running on http://{host}:{port}")
    print(f"  SSE endpoint:     http://{host}:{port}/sse")
    print(f"  Message endpoint: http://{host}:{port}/message")
    print(f"  Health check:     http://{host}:{port}/health")
    print(f"  Database:         {db_path}")
    if server._auth_token:
        print(f"  Auth:             Bearer token required")
    else:
        if host != "127.0.0.1" and host != "localhost":
            print(f"  WARNING: No auth token set. Set OPENMEMO_MCP_TOKEN for security.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        server.server_close()
        mcp.close()


def main():
    import argparse

    parser = argparse.ArgumentParser(
        prog="openmemo-mcp",
        description="OpenMemo MCP Server — Memory for any AI client",
    )
    parser.add_argument(
        "--transport", choices=["stdio", "sse"], default="stdio",
        help="Transport mode (default: stdio)",
    )
    parser.add_argument("--host", default="127.0.0.1", help="SSE server host")
    parser.add_argument("--port", type=int, default=8780, help="SSE server port")
    parser.add_argument(
        "--db", default=os.environ.get("OPENMEMO_DB", "openmemo.db"),
        help="Database path",
    )
    parser.add_argument("--agent-id", default="", help="Agent identifier")
    parser.add_argument("--token", default="", help="Auth token for SSE mode")

    args = parser.parse_args()

    if args.transport == "sse":
        run_sse(host=args.host, port=args.port, db_path=args.db,
                agent_id=args.agent_id, auth_token=args.token)
    else:
        run_stdio(db_path=args.db, agent_id=args.agent_id)


if __name__ == "__main__":
    main()
