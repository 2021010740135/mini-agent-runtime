"""多 session 管理——创建、保存、加载和列出用户会话."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .errors import SessionError
from .session import Session


@dataclass(frozen=True)
class SessionMeta:
    """会话列表中展示的轻量元信息."""

    session_id: str
    user_id: str
    created_at: str
    updated_at: str
    message_count: int


class SessionManager:
    """按 user_id/session_id 管理本地持久化会话."""

    def __init__(self, base_dir: str | Path | None = None) -> None:
        root = Path(__file__).resolve().parent.parent
        self.base_dir = Path(base_dir) if base_dir is not None else root / "data" / "sessions"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def create_session(self, user_id: str = "default") -> Session:
        """创建新 session 并立即持久化."""
        session = Session(user_id=user_id)
        self.save_session(session)
        return session

    def get_session(self, user_id: str, session_id: str) -> Session:
        """加载指定用户的指定 session."""
        path = self._session_path(user_id, session_id)
        if not path.is_file():
            raise SessionError(f"session 不存在: user_id={user_id}, session_id={session_id}")

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            raise SessionError(f"读取 session 失败: {path}") from e

        session = Session.from_dict(data)
        if session.user_id != user_id or session.session_id != session_id:
            raise SessionError(f"session 文件内容与路径不匹配: {path}")
        return session

    def save_session(self, session: Session) -> None:
        """保存 session 到 JSON 文件."""
        path = self._session_path(session.user_id, session.session_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(session.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def list_sessions(self, user_id: str) -> list[SessionMeta]:
        """列出指定用户的 session 元信息，按更新时间倒序排列."""
        user_dir = self.base_dir / self._safe_part(user_id)
        if not user_dir.is_dir():
            return []

        metas: list[SessionMeta] = []
        for path in user_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                session = Session.from_dict(data)
            except Exception:
                continue
            metas.append(SessionMeta(
                session_id=session.session_id,
                user_id=session.user_id,
                created_at=session.created_at.isoformat(),
                updated_at=session.updated_at.isoformat(),
                message_count=len(session.messages),
            ))

        return sorted(metas, key=lambda meta: meta.updated_at, reverse=True)

    def delete_session(self, user_id: str, session_id: str) -> None:
        """删除指定 session；不存在则静默返回."""
        path = self._session_path(user_id, session_id)
        if path.exists():
            path.unlink()

    def _session_path(self, user_id: str, session_id: str) -> Path:
        return self.base_dir / self._safe_part(user_id) / f"{self._safe_part(session_id)}.json"

    @staticmethod
    def _safe_part(value: str) -> str:
        cleaned = "".join(ch if ch.isalnum() or ch in ("-", "_", ".") else "_" for ch in value)
        return cleaned or "default"
