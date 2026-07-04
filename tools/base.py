"""工具基类——定义所有工具的抽象接口"""

from abc import ABC, abstractmethod


class BaseTool(ABC):
    """所有工具的基类."""

    name: str = ""
    description: str = ""

    @abstractmethod
    async def execute(self, **kwargs) -> str:
        """执行工具并返回结果."""
        ...
