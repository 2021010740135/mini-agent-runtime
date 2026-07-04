"""Agent 运行时——核心循环逻辑"""

from .config import Config
from .llm_client import LLMClient


class AgentRuntime:
    """Agent 主控制器，负责编排 LLM 调用、工具执行和决策循环."""

    def __init__(self) -> None:
        self.config = Config()
        self.config.validate()
        self.llm = LLMClient(
            api_key=self.config.api_key,
            base_url=self.config.base_url,
            model=self.config.model,
        )

    def run(self) -> None:
        """启动 Agent 主循环."""
        pass
