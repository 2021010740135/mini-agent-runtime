"""工具注册中心——管理工具的注册、查找和调用"""


class ToolRegistry:
    """工具注册表，管理所有可用工具."""

    def __init__(self) -> None:
        self._tools: dict[str, "BaseTool"] = {}
