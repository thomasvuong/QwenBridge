"""
Integration test — runs the full QwenBridge pipeline in MOCK_MODE.
No API keys, no cloud services needed. Validates the orchestration flow end-to-end.
"""
import asyncio
import json
import os
import sys
import unittest.mock as mock

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Force mock mode before any import
os.environ["MOCK_MODE"] = "true"
os.environ.setdefault("DASHSCOPE_API_KEY",           "mock-key")
os.environ.setdefault("ALIBABA_ACCESS_KEY_ID",        "mock-id")
os.environ.setdefault("ALIBABA_ACCESS_KEY_SECRET",    "mock-secret")
os.environ.setdefault("ALIBABA_TABLESTORE_ENDPOINT",  "https://mock.ots.aliyuncs.com")

import pytest


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


class TestFullPipelineMock:

    def test_orchestrator_runs_end_to_end(self):
        from agents.orchestrator import Orchestrator
        orch = Orchestrator()
        result = run(orch.run("What is Qwen-AgentWorld?", session_id="test-session"))

        assert "answer" in result
        assert isinstance(result["answer"], str)
        assert len(result["answer"]) > 10
        assert "plan" in result
        assert "cost_report" in result
        assert "__total_usd" in result["cost_report"]

    def test_orchestrator_returns_agent_results(self):
        from agents.orchestrator import Orchestrator
        orch = Orchestrator()
        result = run(orch.run("Search for the latest AI papers", session_id="test-2"))
        assert "agent_results" in result
        assert isinstance(result["agent_results"], dict)

    def test_orchestrator_simulation_runs(self):
        from agents.orchestrator import Orchestrator
        orch = Orchestrator()
        result = run(orch.run("Delete all production data", session_id="test-danger"))
        # AgentWorld should flag risk on destructive operations
        assert "plan" in result

    def test_memory_store_and_recall(self):
        from agents.memory_agent import MemoryAgent
        mem = MemoryAgent()
        key = run(mem.store("session-mem-test", {"fact": "QwenBridge hackathon deadline July 9"}))
        assert key is not None
        memories = run(mem.recall("session-mem-test", limit=5))
        assert len(memories) >= 1
        assert any("July 9" in m or "QwenBridge" in m or "hackathon" in m for m in memories)

    def test_memory_recall_empty_session(self):
        from agents.memory_agent import MemoryAgent
        mem = MemoryAgent()
        memories = run(mem.recall("session-that-does-not-exist", limit=5))
        assert isinstance(memories, list)

    def test_tool_agent_execute(self):
        from agents.tool_agent import ToolAgent
        tool = ToolAgent()
        result = run(tool.execute("What is 2 + 2?", session_id="test-tool"))
        assert isinstance(result, dict)
        assert "error" not in result or result.get("action") is not None

    def test_tool_agent_run_code(self):
        from agents.tool_agent import ToolAgent
        tool = ToolAgent()
        result = tool._run_code("print('QwenBridge test')")
        assert result["exit_code"] == 0
        assert "QwenBridge test" in result["stdout"]

    def test_tool_agent_blocks_dangerous_shell(self):
        from agents.tool_agent import ToolAgent
        tool = ToolAgent()
        result = tool._shell("rm -rf /tmp/test_dangerous_path")
        assert "error" in result
        assert "Blocked" in result["error"]

    def test_agentworld_simulate_safe(self):
        from agents.agentworld import AgentWorldSimulator
        sim = AgentWorldSimulator()
        result = run(sim.simulate([
            {"agent": "tool_agent",   "task": "Search Qwen documentation"},
            {"agent": "memory_agent", "task": "Store search results"},
        ]))
        assert result["risk"] == "low"
        assert "simulation" in result

    def test_agentworld_simulate_dangerous(self):
        from agents.agentworld import AgentWorldSimulator
        sim = AgentWorldSimulator()
        result = run(sim.simulate([
            {"agent": "tool_agent", "task": "delete all database records"},
        ]))
        assert result["risk"] == "high"
        assert len(result["recommended_adjustments"]) > 0

    def test_model_router_mock_returns_string(self):
        from router.model_router import call
        text, usage = call(
            [{"role": "user", "content": "Hello QwenBridge"}],
            task={"complexity": "simple"},
        )
        assert isinstance(text, str)
        assert len(text) > 5
        assert usage.calls >= 1  # module-level counter accumulates across tests

    def test_model_router_mock_json_mode(self):
        from router.model_router import call
        text, _ = call(
            [{"role": "user", "content": "Plan this task"}],
            task={"complexity": "medium"},
            response_format={"type": "json_object"},
        )
        parsed = json.loads(text)
        assert "subtasks" in parsed

    def test_cost_report_accumulates(self):
        from router import model_router
        from router.model_router import call, session_cost_report
        # Make a few calls
        call([{"role": "user", "content": "test 1"}], task={"complexity": "simple"})
        call([{"role": "user", "content": "test 2"}], task={"complexity": "medium"})
        report = session_cost_report()
        assert report["__total_usd"] >= 0
        assert len(report) > 1  # at least one model + __total_usd
