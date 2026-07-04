"""测试 DecisionEngine"""

from agent.decision import DecisionEngine


def test_decision_engine_creation():
    """验证 DecisionEngine 可被实例化."""
    engine = DecisionEngine()
    assert engine is not None
