"""
OpenMemo Agent Memory Demo

Demonstrates how OpenMemo provides persistent memory for AI agents.
Works with any agent framework through the Universal Adapter Layer.

Run:
    python cookbooks/agent_memory_demo.py
"""

from openmemo import Memory


def demo_basic_memory():
    print("=" * 60)
    print("Demo 1: Basic Agent Memory")
    print("=" * 60)

    memory = Memory(db_path=":memory:")

    memory.write_memory("User prefers Python for backend development",
                        scene="coding", memory_type="preference", confidence=0.9)
    memory.write_memory("Always deploy using Docker Compose",
                        scene="deployment", memory_type="constraint", confidence=0.95)
    memory.write_memory("PostgreSQL is the production database",
                        scene="infrastructure", memory_type="decision", confidence=0.9)

    result = memory.recall_context("What language for backend?", scene="coding")
    print("\nRecall: 'What language for backend?'")
    for ctx in result.get("context", []):
        print(f"  → {ctx}")

    result = memory.recall_context("How to deploy?", scene="deployment")
    print("\nRecall: 'How to deploy?'")
    for ctx in result.get("context", []):
        print(f"  → {ctx}")

    print()


def demo_openclaw_adapter():
    print("=" * 60)
    print("Demo 2: OpenClaw Agent with Memory")
    print("=" * 60)

    from openmemo.adapters.openclaw import OpenClawMemoryBackend

    memory = Memory(db_path=":memory:")
    backend = OpenClawMemoryBackend(memory=memory, agent_id="claw_agent")

    backend.on_action("Set up Flask API server", scene="coding")
    backend.on_task_complete("deploy backend", "Deployed using Docker Compose",
                            scene="deployment")
    backend.on_observation("Tests passed with 95% coverage", scene="testing")

    prompt = "How should I deploy the backend?"
    injected = backend.inject_context(prompt, query="deploy backend Docker")
    print(f"\nOriginal prompt: {prompt}")
    print(f"Injected prompt:\n{injected}")

    metrics = backend.get_metrics()
    print(f"\nMetrics: {metrics}")
    print()


def demo_langchain_adapter():
    print("=" * 60)
    print("Demo 3: LangChain Agent with Memory")
    print("=" * 60)

    from openmemo.adapters.langchain import OpenMemoMemory

    memory = Memory(db_path=":memory:")
    lc_memory = OpenMemoMemory(memory=memory, agent_id="lc_agent")

    lc_memory.save_context(
        {"input": "What database should I use for production?"},
        {"output": "I recommend PostgreSQL for production workloads due to its reliability."},
    )
    lc_memory.save_context(
        {"input": "How do I deploy my app?"},
        {"output": "Use Docker Compose for consistent deployments."},
    )

    result = lc_memory.load_memory_variables({"input": "database recommendation"})
    print(f"\nLangChain memory variables: {result}")
    print()


def demo_crewai_adapter():
    print("=" * 60)
    print("Demo 4: CrewAI Multi-Agent Memory")
    print("=" * 60)

    from openmemo.adapters.crewai_adapter import CrewAIMemory

    memory = Memory(db_path=":memory:")

    researcher = CrewAIMemory(memory=memory, agent_id="researcher",
                               crew_id="dev_team", default_scene="research")
    coder = CrewAIMemory(memory=memory, agent_id="coder",
                          crew_id="dev_team", default_scene="coding")

    researcher.on_task_start("Research best practices for API design")
    researcher.on_task_complete("Research best practices for API design",
                                "REST with OpenAPI spec is recommended")

    coder.on_agent_action("coder", "Implemented REST API with Flask")
    coder.on_task_complete("Build API", "API deployed at /api/v1")

    print("\nResearcher's context for 'API design':")
    ctx = researcher.get_crew_context("API design best practices")
    for c in ctx:
        print(f"  → {c}")

    print("\nCoder's context for 'API implementation':")
    ctx = coder.get_crew_context("API implementation Flask")
    for c in ctx:
        print(f"  → {c}")
    print()


def demo_mcp_adapter():
    print("=" * 60)
    print("Demo 5: MCP Server for Claude")
    print("=" * 60)

    from openmemo.adapters.mcp import OpenMemoMCPServer

    memory = Memory(db_path=":memory:")
    server = OpenMemoMCPServer(memory=memory, agent_id="claude")

    tools = server.get_tools()
    print(f"\nMCP tools available: {[t['name'] for t in tools]}")

    server.handle_tool("write_memory", {
        "content": "User's project uses React + TypeScript frontend",
        "scene": "coding",
        "memory_type": "fact",
    })

    result = server.handle_tool("recall_memory", {
        "query": "frontend technology stack",
    })
    print(f"Recall result: {result}")
    print()


def demo_context_injection():
    print("=" * 60)
    print("Demo 6: Context Injection Flow")
    print("=" * 60)

    from openmemo.adapters.base_adapter import BaseMemoryAdapter

    memory = Memory(db_path=":memory:")
    adapter = BaseMemoryAdapter(memory=memory, agent_id="demo",
                                 default_scene="general")

    adapter.write_memory("User prefers Python backend", memory_type="preference")
    adapter.write_memory("Production database is PostgreSQL", memory_type="fact")
    adapter.write_memory("Deploy using Docker Compose", memory_type="constraint")

    user_question = "How should I set up the backend?"
    injected_prompt = adapter.inject_context(user_question,
                                              query="backend setup Python Docker PostgreSQL")

    print(f"\nUser question: {user_question}")
    print(f"\nFull prompt sent to LLM:")
    print("-" * 40)
    print(injected_prompt)
    print("-" * 40)
    print()


if __name__ == "__main__":
    demo_basic_memory()
    demo_openclaw_adapter()
    demo_langchain_adapter()
    demo_crewai_adapter()
    demo_mcp_adapter()
    demo_context_injection()
    print("All demos completed successfully!")
