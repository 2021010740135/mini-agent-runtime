"""Agent 运行时——核心循环逻辑"""

from .config import Config
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
        self.memory = MemoryStore(max_history=10)
        self.logger.info("AgentRuntime 初始化完成")

    def run(self) -> None:
        """启动 Agent 主循环——交互式对话（带记忆）."""
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
                messages = self.memory.get_context(SYSTEM_PROMPT)
                reply = self.llm.chat(messages)
            except LLMError as e:
                self.logger.error(f"对话失败: {e}")
                print(f"[错误] {e}")
                continue

            self.memory.add_assistant_message(reply)
            print(f"\nAI: {reply}")
            self.logger.debug(f"AI 回复 (短): {reply[:50]}...")

    def _print_welcome(self) -> None:
        """打印欢迎信息."""
        print("=" * 50)
        print("  Mini Agent Runtime")
        print(f"  模型: {self.config.model}")
        print("  输入 'quit' 或 'exit' 退出")
        print("=" * 50)