"""测试 Session"""

from agent.session import Session


def test_session_creation():
    """验证 Session 创建时自动生成 session_id."""
    session = Session()
    assert session.session_id
    assert len(session.session_id) == 32
