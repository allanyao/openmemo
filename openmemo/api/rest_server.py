"""
OpenMemo REST Server.

Provides HTTP API access to OpenMemo.
Install with: pip install openmemo[server]

Usage:
    python -m openmemo.api.rest_server
"""

import json
import os

try:
    from flask import Flask, request, jsonify
    from flask_cors import CORS
except ImportError:
    raise ImportError("Install server dependencies: pip install openmemo[server]")

from openmemo.api.sdk import Memory


def create_app(db_path: str = None) -> Flask:
    app = Flask(__name__)
    CORS(app)

    db = db_path or os.environ.get("OPENMEMO_DB", "openmemo.db")
    from openmemo.storage.sqlite_store import SQLiteStore
    store = SQLiteStore(db_path=db, check_same_thread=False)
    memory = Memory(db_path=db, store=store)

    @app.route("/")
    def index():
        return jsonify({
            "service": "OpenMemo API",
            "version": "0.1.0",
            "description": "The Memory Architecture for AI Systems",
            "status": "running",
            "docs": "https://openmemo.ai/docs",
            "github": "https://github.com/openmemoai/openmemo",
            "endpoints": {
                "health": "GET /health",
                "add_memory": "POST /api/memories",
                "recall": "POST /api/memories/recall",
                "reconstruct": "POST /api/memories/reconstruct",
                "maintain": "POST /api/maintain",
                "stats": "GET /api/stats",
            },
            "quickstart": {
                "install": "pip install git+https://github.com/openmemoai/openmemo.git",
                "example": 'curl -X POST https://api.openmemo.ai/api/memories -H "Content-Type: application/json" -d \'{"content": "User prefers dark mode"}\'',
            },
        })

    @app.route("/health")
    def health():
        return jsonify({"status": "ok", "service": "openmemo", "version": "0.1.0"})

    @app.route("/api/memories", methods=["POST"])
    def add_memory():
        data = request.get_json()
        if not data or "content" not in data:
            return jsonify({"error": "content is required"}), 400

        note_id = memory.add(
            content=data["content"],
            source=data.get("source", "api"),
            metadata=data.get("metadata", {}),
        )
        return jsonify({"id": note_id}), 201

    @app.route("/api/memories/recall", methods=["POST"])
    def recall():
        data = request.get_json()
        if not data or "query" not in data:
            return jsonify({"error": "query is required"}), 400

        results = memory.recall(
            query=data["query"],
            top_k=data.get("top_k", 10),
            budget=data.get("budget", 2000),
        )
        return jsonify({"results": results})

    @app.route("/api/memories/reconstruct", methods=["POST"])
    def reconstruct():
        data = request.get_json()
        if not data or "query" not in data:
            return jsonify({"error": "query is required"}), 400

        result = memory.reconstruct(
            query=data["query"],
            max_sources=data.get("max_sources", 10),
        )
        return jsonify(result)

    @app.route("/api/maintain", methods=["POST"])
    def maintain():
        result = memory.maintain()
        return jsonify(result)

    @app.route("/api/stats")
    def stats():
        return jsonify(memory.stats())

    return app


if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
