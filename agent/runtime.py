"""Agent 运行时——核心循环逻辑."""

from .config import Config
from .context import ContextManager
from .decision import DecisionEngine
from .llm_client import LLMClient
from .logger import AgentLogger
from .memory import MemoryStore
from .prompts import SYSTEM_PROMPT
from .session import Session
from .session_manager import SessionManager, SessionMeta


class AgentRuntime:
    """Agent 主控制器，负责编排 LLM 调用、工具执行和 session 状态."""

    def __init__(self, session_manager: SessionManager | None = None) -> None:
        self.logger = AgentLogger()
        self.config = Config()
        self.config.validate()
        self.llm = LLMClient(
            api_key=self.config.api_key,
            base_url=self.config.base_url,
            model=self.config.model,
        )
        self.session_manager = session_manager or SessionManager()
        self.current_user_id = "default"
        self.current_session_id: str | None = None
        self.memory = MemoryStore(max_history=200)
        self.context = ContextManager(
            max_tokens=4000,
            keep_recent=6,
            llm_client=self.llm,
        )

        # ── 工具注册（局部导入打破循环依赖）──
        from tools.calculator import CalculatorTool
        from tools.mock_search import MockSearchTool
        from tools.read_docs import ReadDocsTool
        from tools.registry import ToolRegistry
        from tools.todo import TodoTool

        self.registry = ToolRegistry()
        self.todo_tool = TodoTool()
        self.registry.register(CalculatorTool())
        self.registry.register(MockSearchTool())
        self.registry.register(self.todo_tool)
        self.registry.register(ReadDocsTool())

        # ── 决策引擎 ──
        self.engine = DecisionEngine(
            llm_client=self.llm,
            tool_registry=self.registry,
            max_iterations=5,
        )

        self.logger.info("AgentRuntime 初始化完成")

    def create_session(self, user_id: str = "default") -> str:
        """创建新 session，并返回 session_id."""
        session = self.session_manager.create_session(user_id)
        self._bind_session(session)
        return session.session_id

    def list_sessions(self, user_id: str = "default") -> list[SessionMeta]:
        """列出指定用户的历史 session."""
        return self.session_manager.list_sessions(user_id)

    async def run_once(
        self,
        user_input: str,
        user_id: str = "default",
        session_id: str | None = None,
    ) -> str:
        """单次交互：用户输入 → LLM（含工具调用）→ 回复。

        Args:
            user_input: 用户输入文本
            user_id: 用户标识，用于隔离不同用户的 session
            session_id: 会话标识；为空时创建新 session

        Returns:
            AI 回复文本。实际使用的 session_id 可从 current_session_id 获取。
        """
        session = self._load_or_create_session(user_id, session_id)
        self.memory.add_user_message(user_input)

        all_msgs = self.memory.get_all_messages()
        optimized = self.context.optimize(SYSTEM_PROMPT, all_msgs)

        try:
            reply = await self.engine.run(optimized)
        except Exception as e:
            self.logger.error(f"决策引擎失败: {e}")
            reply = f"[错误] {e}"

        self.memory.add_assistant_message(reply)
        session.context_summary = self.context.summary
        session.touch()
        self.session_manager.save_session(session)
        return reply

    def run(self) -> None:
        """启动 Agent 主循环——交互式对话（带记忆 + 上下文管理 + 工具调用）."""
        import asyncio

        self._print_welcome()
        session_id = self.create_session("default")
        self.logger.info(f"交互式会话已创建: {session_id}")

        while True:
            try:
                user_input = input("\n你: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n")
                self.logger.info("用户退出对话")
                break

            if not user_input:
                continue

            if user_input.lower() in ("quit", "exit", "退出"):
                self.logger.info("用户主动退出")
                print("再见！")
                break

            self.logger.info(f"用户输入: {user_input}")
            reply = asyncio.run(self.run_once(
                user_input,
                user_id="default",
                session_id=session_id,
            ))
            print(f"\nAI: {reply}")

    def _load_or_create_session(self, user_id: str, session_id: str | None) -> Session:
        if session_id:
            session = self.session_manager.get_session(user_id, session_id)
        else:
            session = self.session_manager.create_session(user_id)
        self._bind_session(session)
        return session

    def _bind_session(self, session: Session) -> None:
        """把 runtime 的 memory/context/tool state 绑定到指定 session."""
        self.current_user_id = session.user_id
        self.current_session_id = session.session_id
        self.memory.bind_session(session)
        self.context.set_summary(session.context_summary)
        self.todo_tool.bind_state(session.tool_state)

    def _print_welcome(self) -> None:
        """打印欢迎信息."""
        print("=" * 50)
        print("  Mini Agent Runtime")
        print(f"  模型: {self.config.model}")
        print(f"  可用工具: {', '.join(self.registry.list_tools())}")
        print("  输入 'quit' 或 'exit' 退出")
        print("=" * 50)