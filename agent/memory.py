"""记忆模块——短期记忆管理，决定发送哪些消息给 LLM."""

import logging

from .session import Session

logger = logging.getLogger("mini-agent")


class MemoryStore:
    """管理 Agent 的短期记忆（对话上下文）.

    职责：
    - 存储当前 session 的对话历史
    - 控制上下文窗口大小（防止超长）
    - 提供 get_context() 供 LLM 调用使用
    """

    def __init__(self, max_history: int = 20, session: Session | None = None) -> None:
        """初始化记忆存储.

        Args:
            max_history: 最多保留的对话轮数（1 轮 = 用户消息 + AI 回复）
            session: 可选的已有 session；不传则创建默认 session
        """
        self.max_history = max_history
        self.session = session or Session()
        logger.debug(f"MemoryStore 初始化完成，max_history={max_history}")

    def bind_session(self, session: Session) -> None:
        """绑定当前 MemoryStore 使用的 session."""
        self.session = session

    def add_user_message(self, content: str) -> None:
        """记录用户消息."""
        self.session.add_message("user", content)

    def add_assistant_message(self, content: str) -> None:
        """记录 AI 回复."""
        self.session.add_message("assistant", content)

    def get_context(self, system_prompt: str) -> list[dict]:
        """返回发送给 LLM 的消息列表.

        结构：[system_prompt] + 最近 max_history 轮对话

        Args:
            system_prompt: 系统提示词

        Returns:
            可直接传给 LLMClient.chat() 的消息列表
        """
        all_messages = self.session.get_messages()
        max_messages = self.max_history * 2  # 每轮 = user + assistant
        recent = all_messages[-max_messages:] if all_messages else []
        return [{"role": "system", "content": system_prompt}] + recent

    def history_count(self) -> int:
        """返回当前存储的消息条数."""
        return len(self.session.messages)

    def get_all_messages(self) -> list[dict]:
        """返回完整对话历史（不截断），供 ContextManager 优化使用."""
        return self.session.get_messages()

    def clear(self) -> None:
        """清空记忆."""
        self.session.clear()
        logger.debug("记忆已清空")