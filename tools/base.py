"""工具基类——定义所有工具的抽象接口"""

from abc import ABC, abstractmethod
from typing import Any


class BaseTool(ABC):
    """所有工具的基类。

    子类必须定义:
    - name: 工具名称（OpenAI function name）
    - description: 工具用途描述
    - parameters: OpenAI function calling 格式的 JSON Schema 参数定义
    - execute(): 工具执行逻辑
    """

    name: str = ""
    description: str = ""
    parameters: dict[str, Any] = {}

    @abstractmethod
    async def execute(self, **kwargs) -> str:
        """执行工具并返回结果。

        Args:
            **kwargs: 工具参数，与 parameters schema 中定义的字段对应

        Returns:
            工具执行结果字符串
        """
        ...

    def to_openai_schema(self) -> dict[str, Any]:
        """生成 OpenAI function calling 格式的工具定义。

        用于构造 chat.completions.create(tools=[...]) 中的 tools 参数。

        Returns:
            {"type": "function", "function": {"name": ..., "description": ..., "parameters": ...}}
        """
        if not self.name:
            raise ValueError("工具 name 不能为空")
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters if self.parameters else {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name!r}>"