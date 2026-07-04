"""LLM 客户端——封装 OpenAI-compatible Chat Completion API"""

from .errors import LLMError


class LLMClient:
    """与 LLM 服务通信的客户端."""

    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
