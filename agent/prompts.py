"""Prompt 模板——管理和组装发送给 LLM 的提示词"""

SYSTEM_PROMPT = """You are a helpful AI assistant with access to tools.
Use tools when needed to answer the user's question accurately."""

TOOL_CALL_PROMPT = """Based on the user's request, decide which tool to call.
Respond in JSON format with: {"tool": "tool_name", "args": {...}}"""
