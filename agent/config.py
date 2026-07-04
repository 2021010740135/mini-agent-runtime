"""配置管理——从 .env 和环境变量读取 LLM 相关配置"""

import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    """LLM 相关的所有配置项."""

    api_key: str = field(
        default_factory=lambda: os.getenv("OPENAI_API_KEY", ""),
    )
    base_url: str = field(
        default_factory=lambda: os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
    )
    model: str = field(
        default_factory=lambda: os.getenv("LLM_MODEL", "gpt-4o-mini"),
    )

    def validate(self) -> None:
        """如果缺少必要配置则抛出异常."""
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY 未设置，请在 .env 文件中配置")
