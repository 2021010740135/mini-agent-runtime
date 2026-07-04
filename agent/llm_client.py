"""LLM 客户端——封装 OpenAI-compatible Chat Completion API"""

import logging
from openai import OpenAI

from .errors import LLMError

logger = logging.getLogger("mini-agent")


class LLMClient:
    """与 LLM 服务通信的客户端.

    职责：
    - 封装 OpenAI-compatible API 调用
    - 统一错误处理（将 openai 异常转为 LLMError）
    - 记录请求和响应日志
    """

    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        logger.info(f"LLMClient 初始化完成，模型: {model}, API: {base_url}")

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """发送对话请求，返回 LLM 回复文本.

        Args:
            messages: OpenAI 格式的消息列表
            temperature: 采样温度，越高越随机 (0~2)
            max_tokens: 最大生成 token 数

        Returns:
            LLM 返回的文本内容

        Raises:
            LLMError: API 调用失败时抛出
        """
        logger.debug(f"发送 LLM 请求，消息数: {len(messages)}")
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as e:
            logger.error(f"LLM API 调用失败: {e}")
            raise LLMError(f"LLM 调用失败: {e}") from e

        content = response.choices[0].message.content or ""
        logger.debug(f"LLM 回复长度: {len(content)} 字符")
        return content

    def stream(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ):
        """流式发送对话请求，逐块返回 LLM 回复.

        Args:
            messages: OpenAI 格式的消息列表
            temperature: 采样温度
            max_tokens: 最大生成 token 数

        Yields:
            每次返回一个文本片段

        Raises:
            LLMError: API 调用失败时抛出
        """
        logger.debug(f"发送流式 LLM 请求，消息数: {len(messages)}")
        try:
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"LLM 流式调用失败: {e}")
            raise LLMError(f"LLM 流式调用失败: {e}") from e