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

logger = logging.getLogger("openmemo.mcp")

SERVER_NAME = "openmemo"
SERVER_VERSION = "0.7.0"
PROTOCOL_VERSION = "2024-11-05"


def _build_mcp_server(db_path, agent_id):
    from openmemo.adapters.mcp import OpenMemoMCPServer
    return OpenMemoMCPServer(db_path=db_path, agent_id=agent_id)


def _handle_jsonrpc(request: dict, mcp, initialized: dict) -> dict:
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

    if method == "notifications/initialized":
        return None

    if method == "ping":
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}

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
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {"type": "text", "text": json.dumps(result, ensure_ascii=False)},
                    ],
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


def run_stdio(db_path: str = "openmemo.db", agent_id: str = ""):
    mcp = _build_mcp_server(db_path, agent_id)
    initialized = {"done": False}

    logger.info("OpenMemo MCP server starting (stdio)")

    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue

            try:
                request = json.loads(line)
            except json.JSONDecodeError:
                error_resp = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": "Parse error"},
                }
                sys.stdout.write(json.dumps(error_resp) + "\n")
                sys.stdout.flush()
                continue

            response = _handle_jsonrpc(request, mcp, initialized)

            if response is not None:
                sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
                sys.stdout.flush()

        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error("MCP stdio error: %s", e)
            break

    mcp.close()


class _SSEHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        logger.debug("SSE HTTP: %s", format % args)

    def do_GET(self):
        if self.path == "/sse":
            self._handle_sse()
        elif self.path == "/health":
            self._respond_json(200, {"status": "ok", "server": SERVER_NAME, "version": SERVER_VERSION})
        else:
            self._respond_json(404, {"error": "not found"})

    def do_POST(self):
        if self.path.startswith("/message"):
            self._handle_message()
        else:
            self._respond_json(404, {"error": "not found"})

    def _handle_sse(self):
        session_id = str(uuid.uuid4())
        self.server._sessions[session_id] = {"initialized": {"done": False}}

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        endpoint_event = f"event: endpoint\ndata: /message?sessionId={session_id}\n\n"
        self.wfile.write(endpoint_event.encode())
        self.wfile.flush()

        self.server._sse_connections[session_id] = self

        logger.info("SSE client connected: %s", session_id)

        try:
            while True:
                threading.Event().wait(1)
        except (BrokenPipeError, ConnectionResetError, Exception):
            pass
        finally:
            self.server._sse_connections.pop(session_id, None)
            self.server._sessions.pop(session_id, None)
            logger.info("SSE client disconnected: %s", session_id)

    def _handle_message(self):
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        session_id = qs.get("sessionId", [None])[0]

        if not session_id or session_id not in self.server._sessions:
            self._respond_json(400, {"error": "invalid session"})
            return

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)

        try:
            request = json.loads(body)
        except json.JSONDecodeError:
            self._respond_json(400, {"error": "invalid JSON"})
            return

        session = self.server._sessions[session_id]
        response = _handle_jsonrpc(request, self.server._mcp, session.get("initialized", {"done": False}))

        self.send_response(202)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(b'{"status":"accepted"}')
        self.wfile.flush()

        if response is not None:
            sse_conn = self.server._sse_connections.get(session_id)
            if sse_conn:
                try:
                    event_data = json.dumps(response, ensure_ascii=False)
                    sse_msg = f"event: message\ndata: {event_data}\n\n"
                    sse_conn.wfile.write(sse_msg.encode())
                    sse_conn.wfile.flush()
                except (BrokenPipeError, Exception) as e:
                    logger.warning("Failed to send SSE response: %s", e)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
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
            db_path: str = "openmemo.db", agent_id: str = ""):
    mcp = _build_mcp_server(db_path, agent_id)

    server = HTTPServer((host, port), _SSEHandler)
    server._mcp = mcp
    server._sessions = {}
    server._sse_connections = {}

    print(f"OpenMemo MCP Server (SSE) running on http://{host}:{port}")
    print(f"  SSE endpoint:     http://{host}:{port}/sse")
    print(f"  Message endpoint: http://{host}:{port}/message")
    print(f"  Health check:     http://{host}:{port}/health")
    print(f"  Database:         {db_path}")

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

    args = parser.parse_args()

    if args.transport == "sse":
        run_sse(host=args.host, port=args.port, db_path=args.db, agent_id=args.agent_id)
    else:
        run_stdio(db_path=args.db, agent_id=args.agent_id)


if __name__ == "__main__":
    main()
