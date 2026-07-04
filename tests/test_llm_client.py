"""测试 LLMClient 模块"""

from unittest.mock import MagicMock, patch

import pytest

from agent.errors import LLMError
from agent.llm_client import LLMClient


def test_llm_client_creation():
    """验证 LLMClient 实例化——属性正确赋值，OpenAI 客户端已创建."""
    client = LLMClient(
        api_key="sk-test",
        base_url="https://api.test.com/v1",
        model="test-model",
    )
    assert client.api_key == "sk-test"
    assert client.base_url == "https://api.test.com/v1"
    assert client.model == "test-model"
    assert client.client is not None


def test_llm_client_chat_success():
    """验证 chat() 成功时返回 LLM 回复文本."""
    client = LLMClient(
        api_key="sk-test",
        base_url="https://api.test.com/v1",
        model="test-model",
    )

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "你好，我是 AI 助手"

    with patch.object(client.client.chat.completions, "create", return_value=mock_response):
        result = client.chat([{"role": "user", "content": "你好"}])

    assert result == "你好，我是 AI 助手"


def test_llm_client_chat_api_error():
    """验证 API 调用失败时抛出 LLMError（而非原始异常）."""
    client = LLMClient(
        api_key="sk-test",
        base_url="https://api.test.com/v1",
        model="test-model",
    )

    with patch.object(
        client.client.chat.completions, "create",
        side_effect=Exception("网络连接超时"),
    ):
        with pytest.raises(LLMError, match="LLM 调用失败"):
            client.chat([{"role": "user", "content": "你好"}])