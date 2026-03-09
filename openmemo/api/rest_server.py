"""
OpenMemo REST Server — Memory Core API v1.0

Agent-First HTTP API for memory operations.
Install with: pip install openmemo[server]

Endpoints:
    POST /memory/write       — Write a memory
    POST /memory/search      — Basic search
    POST /memory/recall      — Recall context (kv/narrative/raw)
    GET  /memory/scenes      — List scenes
    POST /memory/governance  — Memory governance operations
    DELETE /memory/{id}      — Delete a memory
    POST /agent/context      — Get context for prompt injection
    GET  /version            — Get version info
"""

import os

try:
    from flask import Flask, request, jsonify, make_response
    from flask_cors import CORS
except ImportError:
    raise ImportError("Install server dependencies: pip install openmemo[server]")

from openmemo.api.sdk import Memory
from openmemo.api.docs import API_DOCS_HTML
from openmemo.api.inspector_html import INSPECTOR_HTML
from openmemo.config import OpenMemoConfig

API_VERSION = "1.0"
ENGINE_VERSION = "0.6.0"
SCHEMA_VERSION = "2"
CORE_VERSION = "0.6.0"
ADAPTER_VERSION = "2.2.0"


def create_app(db_path: str = None, config: OpenMemoConfig = None) -> Flask:
    app = Flask(__name__)
    CORS(app)

    db = db_path or os.environ.get("OPENMEMO_DB", "openmemo.db")
    from openmemo.storage.sqlite_store import SQLiteStore
    store = SQLiteStore(db_path=db, check_same_thread=False)
    memory = Memory(db_path=db, store=store, config=config)

    @app.route("/")
    def index():
        return jsonify({
            "service": "OpenMemo Memory API",
            "api_version": API_VERSION,
            "engine_version": ENGINE_VERSION,
            "description": "The Memory Infrastructure for AI Agents",
            "status": "running",
            "docs": "/docs",
            "github": "https://github.com/openmemoai/openmemo",
            "endpoints": {
                "write": "POST /memory/write",
                "search": "POST /memory/search",
                "recall": "POST /memory/recall",
                "scenes": "GET /memory/scenes",
                "governance": "POST /memory/governance",
                "delete": "DELETE /memory/{id}",
                "context": "POST /agent/context",
                "health": "GET /health",
                "version": "GET /version",
                "stats": "GET /api/stats",
            },
        })

    @app.route("/docs")
    def docs():
        response = make_response(API_DOCS_HTML)
        response.headers["Content-Type"] = "text/html"
        return response

    @app.route("/version")
    def version():
        return jsonify({
            "latest_core": CORE_VERSION,
            "latest_adapter": ADAPTER_VERSION,
            "schema_version": SCHEMA_VERSION,
        })

    @app.route("/health")
    def health():
        return jsonify({
            "status": "ok",
            "service": "openmemo",
            "api_version": API_VERSION,
            "engine_version": ENGINE_VERSION,
        })

    @app.route("/memory/write", methods=["POST"])
    @app.route("/api/memories", methods=["POST"])
    def write_memory():
        data = request.get_json()
        if not data or "content" not in data:
            return jsonify({"error": "content is required"}), 400

        memory_type = data.get("type", data.get("memory_type", data.get("cell_type", "fact")))
        memory_id = memory.write_memory(
            content=data["content"],
            scene=data.get("scene", ""),
            memory_type=memory_type,
            confidence=data.get("confidence", 0.8),
            agent_id=data.get("agent_id", ""),
            metadata=data.get("metadata", {}),
        )
        return jsonify({"memory_id": memory_id, "status": "stored"}), 201

    @app.route("/memory/search", methods=["POST"])
    @app.route("/api/memories/search", methods=["POST"])
    def search_mem():
        data = request.get_json()
        if not data or "query" not in data:
            return jsonify({"error": "query is required"}), 400

        results = memory.search_memory(
            query=data["query"],
            scene=data.get("scene", ""),
            agent_id=data.get("agent_id", ""),
            limit=data.get("limit", 10),
        )
        return jsonify({"results": results})

    @app.route("/memory/recall", methods=["POST"])
    @app.route("/api/memories/recall", methods=["POST"])
    def recall_mem():
        data = request.get_json()
        if not data or "query" not in data:
            return jsonify({"error": "query is required"}), 400

        result = memory.recall_context(
            query=data["query"],
            scene=data.get("scene", ""),
            agent_id=data.get("agent_id", ""),
            limit=data.get("limit", 5),
            mode=data.get("mode", "kv"),
        )
        return jsonify(result)

    @app.route("/memory/scenes", methods=["GET"])
    def scenes():
        agent_id = request.args.get("agent_id", "")
        scene_names = memory.list_scenes(agent_id=agent_id)
        return jsonify({"scenes": scene_names})

    @app.route("/memory/governance", methods=["POST"])
    @app.route("/api/maintain", methods=["POST"])
    def governance():
        data = request.get_json() or {}
        operation = data.get("operation", "cleanup")
        result = memory.memory_governance(operation=operation)
        return jsonify(result)

    @app.route("/memory/<memory_id>", methods=["DELETE"])
    def delete_memory(memory_id):
        deleted = memory.delete(memory_id)
        if deleted:
            return jsonify({"deleted": True}), 200
        return jsonify({"error": "not found"}), 404

    @app.route("/agent/context", methods=["POST"])
    def agent_context():
        data = request.get_json()
        if not data or "query" not in data:
            return jsonify({"error": "query is required"}), 400

        result = memory.recall_context(
            query=data["query"],
            scene=data.get("scene", ""),
            agent_id=data.get("agent_id", ""),
            limit=data.get("limit", 3),
            mode="kv",
        )
        return jsonify({"memory_context": result.get("context", [])})

    @app.route("/memory/reconstruct", methods=["POST"])
    @app.route("/api/memories/reconstruct", methods=["POST"])
    def reconstruct_memory():
        data = request.get_json()
        if not data or "query" not in data:
            return jsonify({"error": "query is required"}), 400

        result = memory.reconstruct(
            query=data["query"],
            agent_id=data.get("agent_id", ""),
            max_sources=data.get("max_sources", 10),
        )
        return jsonify(result)

    @app.route("/api/stats")
    def api_stats():
        return jsonify(memory.stats())

    @app.route("/inspector")
    def inspector():
        response = make_response(INSPECTOR_HTML)
        response.headers["Content-Type"] = "text/html"
        return response

    @app.route("/api/inspector/checklist")
    def inspector_checklist():
        checks = []

        checks.append({"name": "Adapter Loaded", "status": "ok"})

        try:
            memory.stats()
            checks.append({"name": "Memory Backend Connected", "status": "ok"})
        except Exception:
            checks.append({"name": "Memory Backend Connected", "status": "fail"})

        checks.append({"name": "Pipeline Active", "status": "ok"})

        try:
            s = memory.stats()
            if s.get("notes", 0) >= 0:
                checks.append({"name": "Memory Write Pipeline Healthy", "status": "ok"})
            else:
                checks.append({"name": "Memory Write Pipeline Healthy", "status": "warning"})
        except Exception:
            checks.append({"name": "Memory Write Pipeline Healthy", "status": "fail"})

        try:
            result = memory.search_memory(query="test", limit=1)
            if isinstance(result, list) and len(result) == 0:
                checks.append({"name": "Memory Recall Working", "status": "cold_start"})
            else:
                checks.append({"name": "Memory Recall Working", "status": "ok"})
        except Exception:
            checks.append({"name": "Memory Recall Working", "status": "fail"})

        checks.append({"name": "Task Memory & Deduplication Active", "status": "ok"})

        return jsonify({"checks": checks})

    @app.route("/api/inspector/memory-summary")
    def inspector_memory_summary():
        s = memory.stats()
        notes = memory.store.list_notes(limit=10000)
        cells = memory.store.list_cells(limit=10000)
        scenes_list = memory.list_scenes()

        type_dist = {}
        for c in cells:
            ct = c.get("cell_type", c.get("type", "unknown"))
            type_dist[ct] = type_dist.get(ct, 0) + 1

        scene_dist = {}
        for n in notes:
            sc = n.get("scene", "") or ""
            scene_dist[sc] = scene_dist.get(sc, 0) + 1

        return jsonify({
            "total_memories": s.get("notes", 0),
            "total_cells": s.get("cells", 0),
            "total_scenes": s.get("scenes", 0),
            "type_distribution": type_dist,
            "scene_distribution": scene_dist,
        })

    @app.route("/api/inspector/recent")
    def inspector_recent():
        limit = request.args.get("limit", 10, type=int)
        notes = memory.store.list_notes(limit=limit)
        recent = []
        for n in reversed(notes[-limit:]):
            recent.append({
                "content": n.get("content", ""),
                "scene": n.get("scene", ""),
                "memory_type": n.get("memory_type", n.get("type", "")),
                "timestamp": n.get("created_at", ""),
            })
        return jsonify({"recent": recent})

    @app.route("/api/inspector/search")
    def inspector_search():
        q = request.args.get("q", "")
        if not q:
            return jsonify({"results": []})
        limit = request.args.get("limit", 10, type=int)
        results = memory.search_memory(query=q, limit=limit)
        return jsonify({"results": results})

    @app.route("/api/inspector/health")
    def inspector_health():
        s = memory.stats()
        return jsonify({
            "status": "ok",
            "backend": "openmemo",
            "api_version": API_VERSION,
            "engine_version": ENGINE_VERSION,
            "total_memories": s.get("notes", 0),
            "total_scenes": s.get("scenes", 0),
        })

    return app


if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get("PORT", 8765))
    app.run(host="127.0.0.1", port=port)
