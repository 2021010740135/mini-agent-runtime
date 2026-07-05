"""会话管理——单个会话的数据模型和序列化."""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4
import copy


@dataclass
class Session:
    """表示一次用户会话，存储完整的对话历史和会话级状态."""

    session_id: str = field(default_factory=lambda: uuid4().hex)
    user_id: str = "default"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    messages: list[dict] = field(default_factory=list)
    context_summary: str = ""
    tool_state: dict = field(default_factory=dict)

    def add_message(self, role: str, content: str) -> None:
        """向会话中添加一条消息.

        Args:
            role: 消息角色，如 "user" 或 "assistant"
            content: 消息文本内容
        """
        self.messages.append({"role": role, "content": content})
        self.touch()

    def get_messages(self) -> list[dict]:
        """返回完整对话历史的副本."""
        return copy.deepcopy(self.messages)

    def clear(self) -> None:
        """清空对话历史."""
        self.messages.clear()
        self.context_summary = ""
        self.tool_state.clear()
        self.touch()

    def touch(self) -> None:
        """刷新会话更新时间."""
        self.updated_at = datetime.now()

    def to_dict(self) -> dict:
        """转换为可 JSON 序列化的字典."""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "messages": copy.deepcopy(self.messages),
            "context_summary": self.context_summary,
            "tool_state": copy.deepcopy(self.tool_state),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Session":
        """从 JSON 字典恢复会话对象."""
        created_at = cls._parse_datetime(data.get("created_at"))
        updated_at = cls._parse_datetime(data.get("updated_at"))
        return cls(
            session_id=data.get("session_id") or uuid4().hex,
            user_id=data.get("user_id") or "default",
            created_at=created_at,
            updated_at=updated_at,
            messages=copy.deepcopy(data.get("messages") or []),
            context_summary=data.get("context_summary") or "",
            tool_state=copy.deepcopy(data.get("tool_state") or {}),
        )

    @staticmethod
    def _parse_datetime(value) -> datetime:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str) and value:
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                pass
        return datetime.now()