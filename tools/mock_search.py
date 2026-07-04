"""模拟搜索工具——返回模拟搜索结果"""

from .base import BaseTool


class MockSearchTool(BaseTool):
    """模拟网络搜索，返回预设的搜索结果."""

    name = "search"
    description = "搜索互联网获取信息"
