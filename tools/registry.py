"""工具注册中心——管理工具的注册、查找和调用"""

from agent.errors import ToolError
from .base import BaseTool


class ToolRegistry:
    """工具注册表，管理所有可用工具。

    职责：
    - register() / unregister()：注册与注销工具
    - get()：按名称查找工具实例
    - get_tools_schema()：生成 OpenAI tools 参数列表
    - list_tools()：列出所有已注册工具名称
    """

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    # ── 注册 / 注销 ──────────────────────────

    def register(self, tool: BaseTool) -> None:
        """注册一个工具。

        Args:
            tool: 工具实例

        Raises:
            ToolError: 工具名称为空，或同名工具已存在
        """
        if not tool.name:
            raise ToolError("工具 name 不能为空")
        if tool.name in self._tools:
            raise ToolError(f"工具 '{tool.name}' 已注册")
        self._tools[tool.name] = tool

    def unregister(self, name: str) -> None:
        """注销指定名称的工具。

        Args:
            name: 工具名称

        Raises:
            ToolError: 工具未注册
        """
        if name not in self._tools:
            raise ToolError(f"工具 '{name}' 未注册，无法注销")
        del self._tools[name]

    # ── 查找 ──────────────────────────────────

    def get(self, name: str) -> BaseTool:
        """按名称获取工具实例。

        Args:
            name: 工具名称

        Returns:
            工具实例

        Raises:
            ToolError: 工具未注册
        """
        if name not in self._tools:
            raise ToolError(f"工具 '{name}' 未注册")
        return self._tools[name]

    # ── Schema 生成 ───────────────────────────

    def get_tools_schema(self) -> list[dict]:
        """生成所有已注册工具的 OpenAI tools 参数列表。

        返回值可直接传入 chat.completions.create(tools=...) 的 tools 参数。

        Returns:
            [{"type": "function", "function": {...}}, ...]
        """
        return [tool.to_openai_schema() for tool in self._tools.values()]

    def list_tools(self) -> list[str]:
        """列出所有已注册的工具名称。

        Returns:
            工具名称列表（按注册先后顺序排列）
        """
        return list(self._tools.keys())

    # ── 属性 ──────────────────────────────────

    @property
    def tool_count(self) -> int:
        """已注册的工具数量。"""
        return len(self._tools)

    # ── 魔术方法 ──────────────────────────────

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    def __repr__(self) -> str:
        names = ", ".join(self._tools.keys()) if self._tools else "(空)"
        return f"<ToolRegistry: {names}>"