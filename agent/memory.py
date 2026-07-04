"""记忆模块——短期和长期记忆管理"""


class MemoryStore:
    """存储和管理 Agent 的记忆（短期对话记录和长期知识）."""

    def __init__(self) -> None:
        self.short_term: list[dict] = []
        self.long_term: dict[str, str] = {}
