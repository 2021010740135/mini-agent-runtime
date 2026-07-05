"""待办事项工具——管理 session 级任务列表."""

from .base import BaseTool


class TodoTool(BaseTool):
    """管理待办事项列表。

    支持操作：add（添加）、list（列出）、done（完成）、clear（清空）。
    默认使用实例内存；AgentRuntime 会在每次请求前绑定当前 session 的 tool_state。
    """

    name = "todo"
    description = "管理待办事项列表，支持添加、列出、标记完成、清空操作"

    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["add", "list", "done", "clear"],
                "description": "操作类型：add=添加任务, list=列出所有任务, done=标记完成, clear=清空列表",
            },
            "task": {
                "type": "string",
                "description": "任务内容（add 操作必填，done 操作时为任务编号）",
            },
        },
        "required": ["action"],
    }

    def __init__(self) -> None:
        super().__init__()
        self._tasks: list[dict] = []  # [{"content": ..., "done": bool}]

    def bind_state(self, tool_state: dict) -> None:
        """绑定当前 session 的工具状态，确保不同 session 的 todo 隔离."""
        tasks = tool_state.setdefault("todo", [])
        if not isinstance(tasks, list):
            tasks = []
            tool_state["todo"] = tasks
        self._tasks = tasks

    async def execute(self, **kwargs) -> str:
        """执行待办事项操作。

        Args:
            action: 操作类型 (add / list / done / clear)
            task: 任务内容或编号

        Returns:
            操作结果描述字符串
        """
        action = kwargs.get("action", "").strip().lower()

        handlers = {
            "add": self._add,
            "list": self._list,
            "done": self._done,
            "clear": self._clear,
        }

        if action not in handlers:
            return (
                f"错误：不支持的操作 '{action}'。"
                f"可用操作: {', '.join(handlers.keys())}"
            )

        task = kwargs.get("task", "").strip()
        return handlers[action](task)

    def _add(self, task: str) -> str:
        if not task:
            return "错误：添加任务时 task 参数不能为空"
        # 按 、或 , 或 ，拆分多条任务
        import re
        items = [t.strip() for t in re.split(r"[、,，]", task) if t.strip()]
        added = []
        for item in items:
            self._tasks.append({"content": item, "done": False})
            added.append(f"#{len(self._tasks)} {item}")
        return "已添加任务:\n" + "\n".join(f"  {a}" for a in added)

    def _list(self, _task: str) -> str:
        if not self._tasks:
            return "待办列表为空"
        lines = []
        for i, t in enumerate(self._tasks, 1):
            status = "[x]" if t["done"] else "[ ]"
            lines.append(f"  {i}. {status} {t['content']}")
        return f"待办列表（共 {len(self._tasks)} 项）:\n" + "\n".join(lines)

    def _done(self, task: str) -> str:
        if not task:
            return "错误：标记完成时请提供任务编号（如 '1'）"
        try:
            idx = int(task) - 1
        except ValueError:
            return f"错误：'{task}' 不是有效的任务编号"
        if idx < 0 or idx >= len(self._tasks):
            return f"错误：任务编号 {task} 不存在（共 {len(self._tasks)} 项）"
        self._tasks[idx]["done"] = True
        return f"已标记任务 #{task} 为完成: {self._tasks[idx]['content']}"

    def _clear(self, _task: str) -> str:
        count = len(self._tasks)
        self._tasks.clear()
        return f"已清空全部 {count} 项任务"