"""自定义异常——Agent 运行时的各类错误"""


class AgentError(Exception):
    """Agent 运行时基础异常."""


class LLMError(AgentError):
    """LLM 调用相关错误."""


class ToolError(AgentError):
    """工具执行相关错误."""


class DecisionError(AgentError):
    """决策解析相关错误."""


class ContextLimitError(AgentError):
    """上下文超限错误."""
