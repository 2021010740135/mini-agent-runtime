"""模拟搜索工具——返回预设的搜索结果"""

from .base import BaseTool


class MockSearchTool(BaseTool):
    """模拟网络搜索，根据关键词返回预设结果。

    用于演示 Agent 调用工具的能力，无需真实联网。
    """

    name = "search"
    description = "搜索互联网获取信息，支持按关键词返回模拟结果"

    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "搜索关键词，如 'Python 异步编程'",
            },
        },
        "required": ["query"],
    }

    # 预设的模拟搜索结果
    _MOCK_RESULTS: dict[str, str] = {
        "python": (
            "Python 是一种解释型、面向对象的高级编程语言。"
            "最新稳定版本为 Python 3.12，引入了更多性能优化和类型系统改进。"
        ),
        "异步编程": (
            "Python 异步编程基于 asyncio 库，使用 async/await 语法。"
            "核心概念包括：事件循环（Event Loop）、协程（Coroutine）、"
            "Future 和 Task。适用于 I/O 密集型任务。"
        ),
        "agent": (
            "AI Agent 是能够自主感知环境、做出决策并执行动作的智能体。"
            "核心组件包括：LLM 推理引擎、记忆系统、工具调用、规划模块。"
            "常用框架有 LangChain、AutoGen、CrewAI 等。"
        ),
        "fastapi": (
            "FastAPI 是一个现代、高性能的 Python Web 框架，基于 Starlette 和 Pydantic。"
            "支持自动生成 OpenAPI 文档、依赖注入、异步处理。"
        ),
    }

    async def execute(self, **kwargs) -> str:
        """模拟搜索并返回结果。

        Args:
            query: 搜索关键词

        Returns:
            匹配到的搜索结果字符串，无匹配时返回提示
        """
        query = kwargs.get("query", "").strip()
        if not query:
            return "错误：搜索关键词不能为空"

        # 关键词匹配（大小写不敏感）
        for keyword, result in self._MOCK_RESULTS.items():
            if keyword.lower() in query.lower():
                return f"[搜索结果] 关键词: {keyword}\n{result}"

        # 未匹配到任何关键词
        return (
            f"[搜索结果] 未找到与 '{query}' 直接匹配的信息。\n"
            f"可用的预设关键词: {', '.join(self._MOCK_RESULTS.keys())}"
        )