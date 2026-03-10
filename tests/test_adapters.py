"""Tests for OpenMemo Universal Adapter Layer."""
import pytest
from openmemo.api.sdk import Memory
from openmemo.adapters.base_adapter import BaseMemoryAdapter, AdapterMetrics
from openmemo.adapters.openclaw import OpenClawMemoryBackend
from openmemo.adapters.langchain import OpenMemoMemory
from openmemo.adapters.crewai_adapter import CrewAIMemory
from openmemo.adapters.mcp import OpenMemoMCPServer
from openmemo.adapters.http_adapter import HTTPMemoryClient


@pytest.fixture
def mem():
    return Memory(db_path=":memory:")


class TestAdapterMetrics:
    def test_initial_metrics(self):
        m = AdapterMetrics()
        assert m.writes == 0
        assert m.recalls == 0
        assert m.avg_write_ms == 0
        assert m.avg_recall_ms == 0

    def test_summary(self):
        m = AdapterMetrics()
        m.writes = 5
        m.recalls = 3
        m.total_write_ms = 100
        m.total_recall_ms = 60
        s = m.summary()
        assert s["writes"] == 5
        assert s["avg_write_ms"] == 20.0
        assert s["avg_recall_ms"] == 20.0


class TestBaseAdapter:
    def test_write_and_recall(self, mem):
        adapter = BaseMemoryAdapter(memory=mem, agent_id="test")
        result = adapter.write_memory("Python is great for scripting", memory_type="fact")
        assert result != ""

        results = adapter.recall_memory("Python")
        assert isinstance(results, list)

    def test_recall_context(self, mem):
        adapter = BaseMemoryAdapter(memory=mem, agent_id="test")
        adapter.write_memory("Use Docker for deployment", memory_type="decision")
        result = adapter.recall_context("deployment")
        assert "context" in result

    def test_inject_context_empty(self, mem):
        adapter = BaseMemoryAdapter(memory=mem, agent_id="test")
        prompt = "How to deploy?"
        result = adapter.inject_context(prompt)
        assert result == prompt

    def test_inject_context_with_memory(self, mem):
        adapter = BaseMemoryAdapter(memory=mem, agent_id="test")
        adapter.write_memory("Always use Docker for deployment", memory_type="decision")
        prompt = "How to deploy?"
        result = adapter.inject_context(prompt, query="deploy Docker")
        assert "Relevant memories:" in result
        assert "How to deploy?" in result

    def test_get_context(self, mem):
        adapter = BaseMemoryAdapter(memory=mem, agent_id="test")
        adapter.write_memory("Redis runs on port 6379", memory_type="fact")
        ctx = adapter.get_context("Redis port")
        assert isinstance(ctx, list)

    def test_list_scenes(self, mem):
        adapter = BaseMemoryAdapter(memory=mem, agent_id="test")
        adapter.write_memory("Test content for scene", scene="testing", memory_type="fact")
        scenes = adapter.list_scenes()
        assert isinstance(scenes, list)

    def test_metrics_tracking(self, mem):
        adapter = BaseMemoryAdapter(memory=mem, agent_id="test")
        adapter.write_memory("Test write", memory_type="fact")
        adapter.recall_memory("test")
        metrics = adapter.get_metrics()
        assert metrics["writes"] == 1
        assert metrics["recalls"] == 1

    def test_default_scene(self, mem):
        adapter = BaseMemoryAdapter(memory=mem, agent_id="test", default_scene="coding")
        adapter.write_memory("Python is fast", memory_type="fact")
        assert adapter.default_scene == "coding"

    def test_adapter_name(self):
        assert BaseMemoryAdapter.adapter_name == "base"

    def test_close(self, mem):
        adapter = BaseMemoryAdapter(memory=mem)
        adapter.close()


class TestOpenClawAdapter:
    def test_adapter_name(self):
        assert OpenClawMemoryBackend.adapter_name == "openclaw"

    def test_inherits_base(self, mem):
        backend = OpenClawMemoryBackend(memory=mem, agent_id="claw")
        assert isinstance(backend, BaseMemoryAdapter)

    def test_write_and_search(self, mem):
        backend = OpenClawMemoryBackend(memory=mem, agent_id="claw")
        backend.write_memory("Use Flask for API", memory_type="decision")
        results = backend.search_memory("Flask")
        assert isinstance(results, list)

    def test_lifecycle_hooks(self, mem):
        backend = OpenClawMemoryBackend(memory=mem, agent_id="claw")
        backend.on_action("deployed using docker", scene="deployment")
        backend.on_observation("deployment succeeded", scene="deployment")
        backend.on_task_complete("deploy backend", "success", scene="deployment")
        results = backend.recall_memory("deploy")
        assert len(results) >= 1

    def test_on_thought_noop(self, mem):
        backend = OpenClawMemoryBackend(memory=mem, agent_id="claw")
        backend.on_thought("thinking about deployment")

    def test_backward_compat_write(self, mem):
        backend = OpenClawMemoryBackend(memory=mem, agent_id="claw")
        result = backend.write("Use PostgreSQL", cell_type="decision")
        assert result != ""

    def test_backward_compat_recall(self, mem):
        backend = OpenClawMemoryBackend(memory=mem, agent_id="claw")
        backend.write("Use PostgreSQL for database", cell_type="decision")
        result = backend.recall("PostgreSQL")
        assert "context" in result

    def test_inject_context(self, mem):
        backend = OpenClawMemoryBackend(memory=mem, agent_id="claw")
        backend.write_memory("Always use Docker", memory_type="constraint")
        result = backend.inject_context("How to deploy?", query="Docker deploy")
        assert isinstance(result, str)

    def test_governance(self, mem):
        backend = OpenClawMemoryBackend(memory=mem, agent_id="claw")
        result = backend.memory_governance("cleanup")
        assert isinstance(result, dict)


class TestLangChainAdapter:
    def test_adapter_name(self):
        assert OpenMemoMemory.adapter_name == "langchain"

    def test_inherits_base(self, mem):
        memory = OpenMemoMemory(memory=mem, agent_id="lc")
        assert isinstance(memory, BaseMemoryAdapter)

    def test_memory_variables(self, mem):
        memory = OpenMemoMemory(memory=mem, memory_key="chat_history")
        assert memory.memory_variables == ["chat_history"]

    def test_save_and_load(self, mem):
        memory = OpenMemoMemory(memory=mem, agent_id="lc")
        memory.save_context(
            {"input": "What database should I use?"},
            {"output": "I recommend PostgreSQL for production workloads."},
        )
        result = memory.load_memory_variables({"input": "database recommendation"})
        assert "history" in result

    def test_load_empty_query(self, mem):
        memory = OpenMemoMemory(memory=mem, agent_id="lc")
        result = memory.load_memory_variables({"input": ""})
        assert result == {"history": ""}

    def test_clear_noop(self, mem):
        memory = OpenMemoMemory(memory=mem)
        memory.clear()

    def test_inject_context(self, mem):
        memory = OpenMemoMemory(memory=mem, agent_id="lc")
        memory.write_memory("User prefers Python backend", memory_type="preference")
        result = memory.inject_context("What language?", query="Python backend")
        assert isinstance(result, str)


class TestCrewAIAdapter:
    def test_adapter_name(self):
        assert CrewAIMemory.adapter_name == "crewai"

    def test_inherits_base(self, mem):
        memory = CrewAIMemory(memory=mem, agent_id="researcher")
        assert isinstance(memory, BaseMemoryAdapter)

    def test_crew_id(self, mem):
        memory = CrewAIMemory(memory=mem, crew_id="my_crew")
        assert memory.crew_id == "my_crew"

    def test_task_lifecycle(self, mem):
        memory = CrewAIMemory(memory=mem, agent_id="researcher")
        memory.on_task_start("Research AI memory systems", scene="research")
        memory.on_task_complete("Research AI memory systems",
                                "Found 5 relevant papers", scene="research")
        results = memory.recall_memory("AI memory research")
        assert len(results) >= 1

    def test_agent_action(self, mem):
        memory = CrewAIMemory(memory=mem, agent_id="coder")
        memory.on_agent_action("coder", "Wrote unit tests for API")
        results = memory.recall_memory("unit tests")
        assert isinstance(results, list)

    def test_get_crew_context(self, mem):
        memory = CrewAIMemory(memory=mem, agent_id="planner")
        memory.write_memory("Project uses microservices architecture",
                           memory_type="decision", scene="architecture")
        ctx = memory.get_crew_context("architecture", scene="architecture")
        assert isinstance(ctx, list)

    def test_get_task_memory(self, mem):
        memory = CrewAIMemory(memory=mem, agent_id="dev")
        memory.write_memory("Deployed backend to AWS", memory_type="decision")
        results = memory.get_task_memory("deploy backend")
        assert isinstance(results, list)

    def test_inject_context(self, mem):
        memory = CrewAIMemory(memory=mem, agent_id="analyst")
        memory.write_memory("Revenue grew 20% last quarter", memory_type="fact")
        result = memory.inject_context("What is the revenue trend?",
                                        query="revenue growth quarter")
        assert isinstance(result, str)


class TestMCPAdapter:
    def test_adapter_name(self):
        assert OpenMemoMCPServer.adapter_name == "mcp"

    def test_inherits_base(self, mem):
        server = OpenMemoMCPServer(memory=mem)
        assert isinstance(server, BaseMemoryAdapter)

    def test_get_tools(self, mem):
        server = OpenMemoMCPServer(memory=mem)
        tools = server.get_tools()
        assert len(tools) == 4
        names = [t["name"] for t in tools]
        assert "write_memory" in names
        assert "recall_memory" in names
        assert "search_memory" in names
        assert "list_scenes" in names

    def test_handle_write(self, mem):
        server = OpenMemoMCPServer(memory=mem, agent_id="claude")
        result = server.handle_tool("write_memory", {
            "content": "User prefers dark mode",
            "memory_type": "preference",
        })
        assert result["status"] == "stored"

    def test_handle_recall(self, mem):
        server = OpenMemoMCPServer(memory=mem, agent_id="claude")
        server.handle_tool("write_memory", {
            "content": "Always use TypeScript for frontend",
        })
        result = server.handle_tool("recall_memory", {
            "query": "TypeScript frontend",
        })
        assert "context" in result

    def test_handle_search(self, mem):
        server = OpenMemoMCPServer(memory=mem, agent_id="claude")
        server.handle_tool("write_memory", {
            "content": "Redis is used for caching",
        })
        result = server.handle_tool("search_memory", {
            "query": "Redis caching",
        })
        assert "results" in result

    def test_handle_list_scenes(self, mem):
        server = OpenMemoMCPServer(memory=mem)
        result = server.handle_tool("list_scenes", {})
        assert "scenes" in result

    def test_handle_unknown_tool(self, mem):
        server = OpenMemoMCPServer(memory=mem)
        result = server.handle_tool("nonexistent", {})
        assert "error" in result


class TestHTTPAdapter:
    def test_adapter_name(self):
        assert HTTPMemoryClient.adapter_name == "http"

    def test_init(self):
        client = HTTPMemoryClient(base_url="http://localhost:9999")
        assert client.base_url == "http://localhost:9999"
        assert client.recall_limit == 5

    def test_init_trailing_slash(self):
        client = HTTPMemoryClient(base_url="http://localhost:9999/")
        assert client.base_url == "http://localhost:9999"

    def test_write_graceful_failure(self):
        client = HTTPMemoryClient(base_url="http://localhost:1")
        result = client.write_memory("test content")
        assert result == ""
        assert client.metrics.errors >= 1

    def test_recall_graceful_failure(self):
        client = HTTPMemoryClient(base_url="http://localhost:1")
        results = client.recall_memory("test")
        assert results == []

    def test_inject_context_no_server(self):
        client = HTTPMemoryClient(base_url="http://localhost:1")
        result = client.inject_context("What should I do?")
        assert result == "What should I do?"

    def test_get_metrics(self):
        client = HTTPMemoryClient()
        metrics = client.get_metrics()
        assert "writes" in metrics
        assert "recalls" in metrics

    def test_close_noop(self):
        client = HTTPMemoryClient()
        client.close()


class TestAdapterUniformInterface:
    @pytest.fixture(params=["openclaw", "langchain", "crewai", "mcp"])
    def adapter(self, request, mem):
        if request.param == "openclaw":
            return OpenClawMemoryBackend(memory=mem, agent_id="test")
        elif request.param == "langchain":
            return OpenMemoMemory(memory=mem, agent_id="test")
        elif request.param == "crewai":
            return CrewAIMemory(memory=mem, agent_id="test")
        elif request.param == "mcp":
            return OpenMemoMCPServer(memory=mem, agent_id="test")

    def test_write_memory(self, adapter):
        result = adapter.write_memory("Universal test memory content",
                                       memory_type="fact")
        assert result != ""

    def test_recall_memory(self, adapter):
        adapter.write_memory("Testing recall across all adapters",
                            memory_type="fact")
        results = adapter.recall_memory("recall adapters")
        assert isinstance(results, list)

    def test_recall_context(self, adapter):
        adapter.write_memory("Context test memory for adapters",
                            memory_type="fact")
        result = adapter.recall_context("context adapters")
        assert "context" in result

    def test_inject_context(self, adapter):
        result = adapter.inject_context("What should I do?")
        assert isinstance(result, str)

    def test_get_context(self, adapter):
        result = adapter.get_context("test query")
        assert isinstance(result, list)

    def test_list_scenes(self, adapter):
        result = adapter.list_scenes()
        assert isinstance(result, list)

    def test_get_metrics(self, adapter):
        metrics = adapter.get_metrics()
        assert "writes" in metrics
        assert "recalls" in metrics

    def test_close(self, adapter):
        adapter.close()
