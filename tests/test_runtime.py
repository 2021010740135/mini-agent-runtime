"""测试 AgentRuntime 模块"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent.runtime import AgentRuntime
from agent.session_manager import SessionManager


def _runtime(tmp_path):
    return AgentRuntime(session_manager=SessionManager(base_dir=tmp_path))


def test_runtime_initialization():
    """验证 AgentRuntime 实例化——config、llm、registry、engine 均正确创建."""
    runtime = AgentRuntime()
    assert runtime.config is not None
    assert runtime.llm is not None
    assert runtime.registry is not None
    assert runtime.engine is not None
    assert runtime.registry.tool_count == 4


def test_runtime_chat_flow(tmp_path):
    """模拟一次完整的对话交互——输入→构造消息→engine.run→输出."""
    runtime = _runtime(tmp_path)

    mock_reply = "你好！有什么可以帮你的？"

    # engine.run 是 async，必须用 AsyncMock
    with patch.object(runtime.engine, "run", AsyncMock(return_value=mock_reply)) as mock_run:
        with patch("builtins.input", side_effect=["你好", "quit"]):
            with patch("builtins.print") as mock_print:
                runtime.run()
                mock_run.assert_called_once()
                # 验证 engine.run 收到的 messages 格式正确
                call_args = mock_run.call_args[0][0]
                assert call_args[0]["role"] == "system"
                assert call_args[1]["role"] == "user"
                assert call_args[1]["content"] == "你好"


def test_runtime_llm_error_handling(tmp_path):
    """验证 engine.run 失败时不会崩溃——打印 [错误] 并继续等待输入."""
    runtime = _runtime(tmp_path)

    with patch.object(
        runtime.engine, "run",
        AsyncMock(side_effect=RuntimeError("模拟失败")),
    ):
        with patch("builtins.input", side_effect=["测试", "quit"]):
            with patch("builtins.print") as mock_print:
                runtime.run()
                error_printed = any(
                    "[错误]" in str(call) for call in mock_print.call_args_list
                )
                assert error_printed


def test_runtime_empty_input_skipped(tmp_path):
    """验证空输入被跳过，不触发 engine.run."""
    runtime = _runtime(tmp_path)

    with patch.object(runtime.engine, "run", MagicMock()) as mock_run:
        with patch("builtins.input", side_effect=["", "  ", "quit"]):
            runtime.run()
            mock_run.assert_not_called()


def test_runtime_exit_commands(tmp_path):
    """验证 quit/exit/退出 命令能正常退出，不触发 engine.run."""
    for cmd in ("quit", "exit", "退出"):
        runtime = _runtime(tmp_path)
        with patch.object(runtime.engine, "run", MagicMock()) as mock_run:
            with patch("builtins.input", side_effect=[cmd]):
                runtime.run()
                mock_run.assert_not_called()


@pytest.mark.asyncio
async def test_run_once_creates_and_resumes_independent_sessions(tmp_path):
    """验证同一用户的两个 session 可分别继续，且上下文互不污染."""
    manager = SessionManager(base_dir=tmp_path)
    runtime = AgentRuntime(session_manager=manager)

    with patch.object(
        runtime.engine,
        "run",
        AsyncMock(side_effect=["天气回复", "周报回复", "天气追问回复"]),
    ) as mock_run:
        await runtime.run_once("窗口1：查天气", user_id="user-a")
        session_one_id = runtime.current_session_id

        await runtime.run_once("窗口2：写周报", user_id="user-a")
        session_two_id = runtime.current_session_id

        await runtime.run_once(
            "继续窗口1的问题",
            user_id="user-a",
            session_id=session_one_id,
        )

    assert session_one_id != session_two_id

    third_call_messages = mock_run.call_args_list[2].args[0]
    user_contents = [
        msg["content"]
        for msg in third_call_messages
        if msg.get("role") == "user"
    ]
    assert "窗口1：查天气" in user_contents
    assert "继续窗口1的问题" in user_contents
    assert "窗口2：写周报" not in user_contents

    loaded_one = manager.get_session("user-a", session_one_id)
    loaded_two = manager.get_session("user-a", session_two_id)
    assert [m["content"] for m in loaded_one.get_messages()] == [
        "窗口1：查天气",
        "天气回复",
        "继续窗口1的问题",
        "天气追问回复",
    ]
    assert [m["content"] for m in loaded_two.get_messages()] == [
        "窗口2：写周报",
        "周报回复",
    ]