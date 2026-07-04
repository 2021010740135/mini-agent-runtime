"""文档读取工具——读取项目内的文档文件"""

from .base import BaseTool


class ReadDocsTool(BaseTool):
    """读取指定的文档或文件内容."""

    name = "read_docs"
    description = "读取项目文档"
