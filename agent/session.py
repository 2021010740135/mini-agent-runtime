"""会话管理——会话的生命周期和持久化"""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4


@dataclass
class Session:
    """表示一次用户会话."""

    session_id: str = field(default_factory=lambda: uuid4().hex)
    created_at: datetime = field(default_factory=datetime.now)
    messages: list[dict] = field(default_factory=list)
