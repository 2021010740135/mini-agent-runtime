"""会话管理——会话的生命周期和持久化"""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4
import copy


@dataclass
class Session:
    """表示一次用户会话，存储完整的对话历史."""

    session_id: str = field(default_factory=lambda: uuid4().hex)
    created_at: datetime = field(default_factory=datetime.now)
    messages: list[dict] = field(default_factory=list)

    def add_message(self, role: str, content: str) -> None:
        """向会话中添加一条消息.

        Args:
            role: 消息角色，如 "user" 或 "assistant"
            content: 消息文本内容
        """
        self.messages.append({"role": role, "content": content})

    def get_messages(self) -> list[dict]:
        """返回完整对话历史的副本."""
        return copy.deepcopy(self.messages)

    def clear(self) -> None:
        """清空对话历史."""
        self.messages.clear()
        self.messages = []