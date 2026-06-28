"""Tests for agentworld.py — offline mode only, no model required."""
import pytest
import asyncio
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import unittest.mock as mock
with mock.patch.dict(os.environ, {
    "DASHSCOPE_API_KEY":           "test",
    "ALIBABA_ACCESS_KEY_ID":       "test",
    "ALIBABA_ACCESS_KEY_SECRET":   "test",
    "ALIBABA_TABLESTORE_ENDPOINT": "https://test.ots.aliyuncs.com",
    "AGENTWORLD_MODE":             "offline",
}):
    from agents.agentworld import AgentWorldSimulator


class TestAgentWorld:
    def run(self, coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    def test_safe_subtasks_low_risk(self):
        sim = AgentWorldSimulator()
        result = self.run(sim.simulate([
            {"agent": "tool_agent", "task": "Search for latest Qwen models"},
            {"agent": "memory_agent", "task": "Store the search results"},
        ]))
        assert result["risk"] == "low"

    def test_delete_action_high_risk(self):
        sim = AgentWorldSimulator()
        result = self.run(sim.simulate([
            {"agent": "tool_agent", "task": "delete all records from production database"},
        ]))
        assert result["risk"] == "high"
        assert "destructive" in result["risk_reason"]

    def test_payment_high_risk(self):
        sim = AgentWorldSimulator()
        result = self.run(sim.simulate([
            {"agent": "tool_agent", "task": "process payment for order #123"},
        ]))
        assert result["risk"] == "high"

    def test_result_has_simulation_array(self):
        sim = AgentWorldSimulator()
        result = self.run(sim.simulate([
            {"agent": "tool_agent", "task": "read file"},
        ]))
        assert "simulation" in result
        assert isinstance(result["simulation"], list)

    def test_result_has_adjustments(self):
        sim = AgentWorldSimulator()
        result = self.run(sim.simulate([
            {"agent": "tool_agent", "task": "delete users table"},
        ]))
        assert "recommended_adjustments" in result
        assert len(result["recommended_adjustments"]) > 0

    def test_empty_subtasks(self):
        sim = AgentWorldSimulator()
        result = self.run(sim.simulate([]))
        assert result["risk"] in ("low", "medium", "high")
