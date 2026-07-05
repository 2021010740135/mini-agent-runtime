"""Agent 运行时——核心循环逻辑"""

from .config import Config
from .context import ContextManager
from .decision import DecisionEngine
from .errors import LLMError
from .llm_client import LLMClient
from .logger import AgentLogger
from .memory import MemoryStore
from .prompts import SYSTEM_PROMPT


class AgentRuntime:
    """Agent 主控制器，负责编排 LLM 调用和交互循环."""

    def __init__(self) -> None:
        self.logger = AgentLogger()
        self.config = Config()
        self.config.validate()
        self.llm = LLMClient(
            api_key=self.config.api_key,
            base_url=self.config.base_url,
            model=self.config.model,
        )
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
        self.registry.register(CalculatorTool())
        self.registry.register(MockSearchTool())
        self.registry.register(TodoTool())
        self.registry.register(ReadDocsTool())

        # ── 决策引擎 ──
        self.engine = DecisionEngine(
            llm_client=self.llm,
            tool_registry=self.registry,
            max_iterations=5,
        )

        self.logger.info("AgentRuntime 初始化完成")

    async def run_once(self, user_input: str) -> str:
        """单次交互：用户输入 → LLM（含工具调用）→ 回复。

        Args:
            user_input: 用户输入文本

        Returns:
            AI 回复文本
        """
        self.memory.add_user_message(user_input)

        all_msgs = self.memory.get_all_messages()
        optimized = self.context.optimize(SYSTEM_PROMPT, all_msgs)

        try:
            reply = await self.engine.run(optimized)
        except Exception as e:
            self.logger.error(f"决策引擎失败: {e}")
            reply = f"[错误] {e}"

        self.memory.add_assistant_message(reply)
        return reply

    def run(self) -> None:
        """启动 Agent 主循环——交互式对话（带记忆 + 上下文管理 + 工具调用）."""
        import asyncio

        self._print_welcome()

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
            reply = asyncio.run(self.run_once(user_input))
            print(f"\nAI: {reply}")

    def _print_welcome(self) -> None:
        """打印欢迎信息."""
        print("=" * 50)
        print("  Mini Agent Runtime")
        print(f"  模型: {self.config.model}")
        print(f"  可用工具: {', '.join(self.registry.list_tools())}")
        print("  输入 'quit' 或 'exit' 退出")
        print("=" * 50)