"""Tests for model_router.py — runs fully offline, no API calls."""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


# Patch config before import to avoid env var requirement
import unittest.mock as mock
with mock.patch.dict(os.environ, {
    "DASHSCOPE_API_KEY":         "test-key",
    "ALIBABA_ACCESS_KEY_ID":     "test-id",
    "ALIBABA_ACCESS_KEY_SECRET": "test-secret",
    "ALIBABA_TABLESTORE_ENDPOINT": "https://test.ots.aliyuncs.com",
}):
    import config
    from router.model_router import route, session_cost_report, RoutingDecision


class TestModelRouter:
    def test_route_image_to_vl(self):
        decision = route({"image_url": "https://example.com/img.png"})
        assert decision.model == config.MODEL_VL_32B
        assert decision.task_type == "vision"

    def test_route_reasoning_to_thinking(self):
        decision = route({"requires_reasoning": True})
        assert decision.model == config.MODEL_MAX_THINKING
        assert decision.task_type == "reasoning"

    def test_route_complex_to_thinking(self):
        decision = route({"complexity": "complex"})
        assert decision.model == config.MODEL_MAX_THINKING

    def test_route_code_to_coder(self):
        decision = route({"requires_code": True})
        assert decision.model == config.MODEL_CODER
        assert decision.task_type == "code"

    def test_route_simple_to_turbo(self):
        decision = route({"complexity": "simple"})
        assert decision.model == config.MODEL_TURBO
        assert decision.task_type == "simple"

    def test_route_medium_to_plus(self):
        decision = route({})
        assert decision.model == config.MODEL_PLUS
        assert decision.task_type == "medium"

    def test_route_image_takes_priority_over_code(self):
        decision = route({"image_url": "test.png", "requires_code": True})
        assert decision.model == config.MODEL_VL_32B

    def test_cost_report_empty(self):
        report = session_cost_report()
        assert "__total_usd" in report

    def test_routing_decision_has_costs(self):
        decision = route({"complexity": "simple"})
        assert decision.cost_per_1m_input > 0
        assert decision.cost_per_1m_output > 0
        assert decision.cost_per_1m_input < decision.cost_per_1m_output

    def test_turbo_is_cheapest(self):
        turbo  = route({"complexity": "simple"})
        plus   = route({})
        max_   = route({"complexity": "complex"})
        assert turbo.cost_per_1m_input < plus.cost_per_1m_input < max_.cost_per_1m_input
