"""Tests for multi-session creation, persistence, and isolation."""

import pytest

from agent.errors import SessionError
from agent.session import Session
from agent.session_manager import SessionManager


def test_create_session_persists_json_file(tmp_path):
    manager = SessionManager(base_dir=tmp_path)

    session = manager.create_session("user-a")

    assert session.user_id == "user-a"
    assert session.session_id
    assert (tmp_path / "user-a" / f"{session.session_id}.json").is_file()


def test_save_and_load_session_round_trips_messages_summary_and_tool_state(tmp_path):
    manager = SessionManager(base_dir=tmp_path)
    session = manager.create_session("user-a")
    session.add_message("user", "查天气")
    session.add_message("assistant", "需要调用工具")
    session.context_summary = "用户在查询天气"
    session.tool_state["todo"] = [{"content": "带伞", "done": False}]

    manager.save_session(session)
    loaded = manager.get_session("user-a", session.session_id)

    assert loaded.session_id == session.session_id
    assert loaded.user_id == "user-a"
    assert loaded.get_messages() == session.get_messages()
    assert loaded.context_summary == "用户在查询天气"
    assert loaded.tool_state["todo"] == [{"content": "带伞", "done": False}]


def test_two_sessions_for_same_user_are_isolated(tmp_path):
    manager = SessionManager(base_dir=tmp_path)
    window_one = manager.create_session("user-a")
    window_two = manager.create_session("user-a")

    window_one.add_message("user", "窗口1：查天气")
    window_one.context_summary = "天气上下文"
    window_one.tool_state["todo"] = [{"content": "带伞", "done": False}]
    manager.save_session(window_one)

    window_two.add_message("user", "窗口2：写周报")
    window_two.context_summary = "周报上下文"
    window_two.tool_state["todo"] = [{"content": "提交周报", "done": False}]
    manager.save_session(window_two)

    loaded_one = manager.get_session("user-a", window_one.session_id)
    loaded_two = manager.get_session("user-a", window_two.session_id)

    assert loaded_one.get_messages()[0]["content"] == "窗口1：查天气"
    assert loaded_two.get_messages()[0]["content"] == "窗口2：写周报"
    assert loaded_one.context_summary == "天气上下文"
    assert loaded_two.context_summary == "周报上下文"
    assert loaded_one.tool_state["todo"][0]["content"] == "带伞"
    assert loaded_two.tool_state["todo"][0]["content"] == "提交周报"


def test_list_sessions_returns_only_requested_user(tmp_path):
    manager = SessionManager(base_dir=tmp_path)
    alice_session = manager.create_session("alice")
    manager.create_session("bob")

    sessions = manager.list_sessions("alice")

    assert [s.session_id for s in sessions] == [alice_session.session_id]
    assert sessions[0].user_id == "alice"


def test_get_missing_session_raises_session_error(tmp_path):
    manager = SessionManager(base_dir=tmp_path)

    with pytest.raises(SessionError):
        manager.get_session("user-a", "missing")


def test_session_to_dict_from_dict_round_trip():
    session = Session(user_id="user-a")
    session.add_message("user", "你好")
    session.context_summary = "摘要"
    session.tool_state["todo"] = [{"content": "测试", "done": False}]

    restored = Session.from_dict(session.to_dict())

    assert restored.session_id == session.session_id
    assert restored.user_id == "user-a"
    assert restored.get_messages() == [{"role": "user", "content": "你好"}]
    assert restored.context_summary == "摘要"
    assert restored.tool_state == {"todo": [{"content": "测试", "done": False}]}
