"""测试 Session 模块"""

from agent.session import Session


def test_session_creation():
    """验证 Session 创建时自动生成 session_id."""
    session = Session()
    assert session.session_id
    assert len(session.session_id) == 32
    assert session.messages == []


def test_session_add_message():
    """验证 add_message 正确添加消息."""
    session = Session()
    session.add_message("user", "你好")
    session.add_message("assistant", "你好！有什么可以帮你的？")

    assert len(session.messages) == 2
    assert session.messages[0] == {"role": "user", "content": "你好"}
    assert session.messages[1] == {"role": "assistant", "content": "你好！有什么可以帮你的？"}


def test_session_clear():
    """验证 clear 清空消息列表."""
    session = Session()
    session.add_message("user", "测试")
    session.clear()

    assert session.messages == []


def test_session_get_messages_returns_copy():
    """验证 get_messages 返回拷贝，外部修改不影响原始数据."""
    session = Session()
    session.add_message("user", "你好")

    msgs = session.get_messages()
    msgs[0]["content"] = "被修改了"

    assert session.messages[0]["content"] == "你好"


def test_session_unique_ids():
    """验证不同 Session 实例有不同的 session_id."""
    s1 = Session()
    s2 = Session()
    assert s1.session_id != s2.session_id