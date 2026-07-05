"""Agent 运行时——核心循环逻辑"""

from .config import Config
from .context import ContextManager
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
        self.logger.info("AgentRuntime 初始化完成")

    def run(self) -> None:
        """启动 Agent 主循环——交互式对话（带记忆 + 上下文管理）."""
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
            self.memory.add_user_message(user_input)

            try:
                all_msgs = self.memory.get_all_messages()
                optimized = self.context.optimize(SYSTEM_PROMPT, all_msgs)
                reply = self.llm.chat(optimized)
            except LLMError as e:
                self.logger.error(f"对话失败: {e}")
                print(f"[错误] {e}")
                continue

            self.memory.add_assistant_message(reply)
            print(f"\nAI: {reply}")

    def _print_welcome(self) -> None:
        """打印欢迎信息."""
        print("=" * 50)
        print("  Mini Agent Runtime")
        print(f"  模型: {self.config.model}")
        print("  输入 'quit' 或 'exit' 退出")
        print("=" * 50)