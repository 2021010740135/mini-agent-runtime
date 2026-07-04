"""上下文管理——消息历史和上下文窗口控制"""


class ContextManager:
    """管理对话历史，处理上下文窗口限制."""

    def __init__(self, max_tokens: int = 128_000) -> None:
        self.max_tokens = max_tokens
