"""测试 AgentRuntime 模块"""

from unittest.mock import patch

import pytest

from agent.errors import LLMError
from agent.runtime import AgentRuntime


def test_runtime_initialization():
    """验证 AgentRuntime 实例化——config 和 llm 均正确创建."""
    runtime = AgentRuntime()
    assert runtime.config is not None
    assert runtime.llm is not None


def test_runtime_chat_flow():
    """模拟一次完整的对话交互——输入→构造消息→调 LLM→输出."""
    runtime = AgentRuntime()

    mock_reply = "你好！有什么可以帮你的？"

    with patch.object(runtime.llm, "chat", return_value=mock_reply) as mock_chat:
        with patch("builtins.input", side_effect=["你好", "quit"]):
            with patch("builtins.print") as mock_print:
                runtime.run()
                mock_chat.assert_called_once()
                call_args = mock_chat.call_args[0][0]
                assert call_args[0]["role"] == "system"
                assert call_args[1]["role"] == "user"
                assert call_args[1]["content"] == "你好"


def test_runtime_llm_error_handling():
    """验证 LLM 调用失败时不会崩溃——打印错误并继续等待输入."""
    runtime = AgentRuntime()

    with patch.object(runtime.llm, "chat", side_effect=LLMError("模拟失败")):
        with patch("builtins.input", side_effect=["测试", "quit"]):
            with patch("builtins.print") as mock_print:
                runtime.run()
                error_printed = any(
                    "[错误]" in str(call) for call in mock_print.call_args_list
                )
                assert error_printed


def test_runtime_empty_input_skipped():
    """验证空输入被跳过，不触发 LLM 调用."""
    runtime = AgentRuntime()

    with patch.object(runtime.llm, "chat") as mock_chat:
        with patch("builtins.input", side_effect=["", "  ", "quit"]):
            runtime.run()
            mock_chat.assert_not_called()


def test_runtime_exit_commands():
    """验证 quit/exit/退出 命令能正常退出."""
    runtime = AgentRuntime()

    for cmd in ("quit", "exit", "退出"):
        with patch.object(runtime.llm, "chat") as mock_chat:
            with patch("builtins.input", side_effect=[cmd]):
                runtime.run()
                mock_chat.assert_not_called()