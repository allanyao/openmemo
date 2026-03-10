"""
MCP (Model Context Protocol) Adapter for OpenMemo.

Allows OpenMemo to serve as a memory backend for
Claude and other MCP-compatible AI assistants.

Usage (local):
    from openmemo.adapters.mcp import OpenMemoMCPServer
    server = OpenMemoMCPServer()

Usage (remote):
    from openmemo.adapters.mcp import OpenMemoMCPServer
    server = OpenMemoMCPServer(base_url="https://api.openmemo.ai")
"""

from openmemo.adapters.base_adapter import BaseMemoryAdapter


class OpenMemoMCPServer(BaseMemoryAdapter):
    adapter_name = "mcp"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get_tools(self):
        return [
            {
                "name": "write_memory",
                "description": "Store a memory. Use this to remember facts, decisions, preferences, or observations.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "content": {"type": "string", "description": "The memory content to store"},
                        "scene": {"type": "string", "description": "Context scene (e.g., 'coding', 'deployment')"},
                        "memory_type": {"type": "string", "enum": ["fact", "decision", "preference", "constraint", "observation"]},
                        "confidence": {"type": "number", "description": "Confidence level 0-1", "default": 0.8},
                        "agent_id": {"type": "string", "description": "Agent identifier"},
                    },
                    "required": ["content"],
                },
            },
            {
                "name": "recall_memory",
                "description": "Recall relevant memories for agent reasoning. Returns contextually relevant past memories.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "What to recall"},
                        "scene": {"type": "string", "description": "Filter by scene"},
                        "limit": {"type": "integer", "description": "Max results", "default": 5},
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "search_memory",
                "description": "Search memories by query. Returns scored results.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "scene": {"type": "string", "description": "Filter by scene"},
                        "limit": {"type": "integer", "description": "Max results", "default": 10},
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "list_scenes",
                "description": "List all memory scenes.",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            },
        ]

    def handle_tool(self, tool_name: str, arguments: dict) -> dict:
        if tool_name == "write_memory":
            memory_id = self.write_memory(
                content=arguments["content"],
                scene=arguments.get("scene", ""),
                memory_type=arguments.get("memory_type", "fact"),
                confidence=arguments.get("confidence", 0.8),
            )
            return {"memory_id": memory_id, "status": "stored"}

        elif tool_name == "recall_memory":
            return self.recall_context(
                query=arguments["query"],
                scene=arguments.get("scene", ""),
                limit=arguments.get("limit", 5),
            )

        elif tool_name == "search_memory":
            results = self.recall_memory(
                query=arguments["query"],
                scene=arguments.get("scene", ""),
                limit=arguments.get("limit", 10),
            )
            return {"results": results}

        elif tool_name == "list_scenes":
            return {"scenes": self.list_scenes()}

        return {"error": f"Unknown tool: {tool_name}"}
