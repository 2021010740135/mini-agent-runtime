"""测试 AgentRuntime 模块"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent.runtime import AgentRuntime


def test_runtime_initialization():
    """验证 AgentRuntime 实例化——config、llm、registry、engine 均正确创建."""
    runtime = AgentRuntime()
    assert runtime.config is not None
    assert runtime.llm is not None
    assert runtime.registry is not None
    assert runtime.engine is not None
    assert runtime.registry.tool_count == 4


def test_runtime_chat_flow():
    """模拟一次完整的对话交互——输入→构造消息→engine.run→输出."""
    runtime = AgentRuntime()

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


def test_runtime_llm_error_handling():
    """验证 engine.run 失败时不会崩溃——打印 [错误] 并继续等待输入."""
    runtime = AgentRuntime()

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


def test_runtime_empty_input_skipped():
    """验证空输入被跳过，不触发 engine.run."""
    runtime = AgentRuntime()

    with patch.object(runtime.engine, "run", MagicMock()) as mock_run:
        with patch("builtins.input", side_effect=["", "  ", "quit"]):
            runtime.run()
            mock_run.assert_not_called()


def test_runtime_exit_commands():
    """验证 quit/exit/退出 命令能正常退出，不触发 engine.run."""
    runtime = AgentRuntime()

    for cmd in ("quit", "exit", "退出"):
        with patch.object(runtime.engine, "run", MagicMock()) as mock_run:
            with patch("builtins.input", side_effect=[cmd]):
                runtime.run()
                mock_run.assert_not_called()