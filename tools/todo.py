"""待办事项工具——管理任务列表"""

from .base import BaseTool


class TodoTool(BaseTool):
    """用于创建和管理待办事项列表."""

    name = "todo"
    description = "管理待办事项列表"
