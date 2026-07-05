"""决策引擎——LLM 工具调用循环"""

import json
import logging
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field

from .errors import DecisionError, ToolError
from .llm_client import LLMClient

logger = logging.getLogger("mini-agent")


# ═══════════════════════════════════════
# 数据结构
# ═══════════════════════════════════════

@dataclass
class ToolCall:
    """一次工具调用请求."""
    id: str
    name: str
    arguments: dict


@dataclass
class Decision:
    """LLM 单次决策的结果."""
    content: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    thought: str | None = None

    @property
    def is_final(self) -> bool:
        """是否不需要进一步调用工具（可直接返回给用户）."""
        return len(self.tool_calls) == 0


# ═══════════════════════════════════════
# 决策引擎
# ═══════════════════════════════════════

class DecisionEngine:
    """管理 LLM 工具调用循环。

    数据流:
      messages + tools → LLM
        ├─ 无 tool_calls → 返回文本回复（终止）
        └─ 有 tool_calls → 执行工具 → 结果追加到 messages → 再次调用 LLM

    依赖注入: LLMClient + ToolRegistry
    """

    def __init__(
        self,
        llm_client: LLMClient,
        tool_registry: "ToolRegistry",
        max_iterations: int = 5,
    ) -> None:
        self.llm = llm_client
        self.registry = tool_registry
        self.max_iterations = max_iterations
        logger.info(
            f"DecisionEngine 初始化完成，已注册 {self.registry.tool_count} 个工具"
        )

    async def run(self, messages: list[dict]) -> str:
        """执行工具调用循环，直到 LLM 返回最终文本回复。

        Args:
            messages: 对话消息列表（含 system prompt）

        Returns:
            LLM 的最终文本回复

        Raises:
            DecisionError: 超过最大迭代次数
        """
        if not self.registry.get_tools_schema():
            # 无工具时直接调用 LLM 返回结果
            return self.llm.chat(messages)

        iteration = 0

        while iteration < self.max_iterations:
            iteration += 1
            logger.debug(f"决策循环 第 {iteration}/{self.max_iterations} 轮")

            decision = self._call_llm(messages)

            if decision.is_final:
                logger.debug(f"LLM 返回最终回复，长度: {len(decision.content or '')}")
                return decision.content or ""

            # 执行本轮所有工具调用
            for tc in decision.tool_calls:
                result = await self._execute_tool_call(tc)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })

        raise DecisionError(
            f"超过最大迭代次数 ({self.max_iterations})，未得到最终回复"
        )

    async def run_stream(
        self, messages: list[dict],
    ) -> AsyncGenerator[dict, None]:
        """流式版工具调用循环，实时 yield 文本和工具调用事件。

        Yields:
            {"type": "text", "content": "..."}   → 逐字文本
            {"type": "tool_result", "name": "...", "content": "..."}  → 工具结果
            {"type": "done"}                     → 结束

        Raises:
            DecisionError: 超过最大迭代次数
        """
        import asyncio

        tools = self.registry.get_tools_schema()
        if not tools:
            for chunk in self.llm.stream(messages):
                yield {"type": "text", "content": chunk}
            yield {"type": "done"}
            return

        iteration = 0

        while iteration < self.max_iterations:
            iteration += 1
            logger.debug(f"决策循环（流式）第 {iteration}/{self.max_iterations} 轮")

            # ── 流式调用 LLM ──
            collected: dict[int, dict] = {}
            streamed_text = ""
            finish_reason = None

            stream = self.llm.client.chat.completions.create(
                model=self.llm.model,
                messages=messages,
                tools=tools,
                stream=True,
            )

            for chunk in stream:
                delta = chunk.choices[0].delta
                finish_reason = chunk.choices[0].finish_reason or finish_reason

                if delta.content:
                    streamed_text += delta.content
                    yield {"type": "text", "content": delta.content}
                    await asyncio.sleep(0)

                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        idx = tc.index
                        if idx not in collected:
                            collected[idx] = {"id": "", "name": "", "arguments": ""}
                        if tc.id:
                            collected[idx]["id"] = tc.id
                        if tc.function and tc.function.name:
                            collected[idx]["name"] = tc.function.name
                        if tc.function and tc.function.arguments:
                            collected[idx]["arguments"] += tc.function.arguments

            # ── 构建 assistant 消息 ──
            assistant_msg: dict = {"role": "assistant"}
            if streamed_text:
                assistant_msg["content"] = streamed_text

            # ── 解析 tool_calls ──
            parsed_calls: list[ToolCall] = []
            if collected and finish_reason == "tool_calls":
                tool_call_blocks = []
                for idx in sorted(collected):
                    tc_data = collected[idx]
                    try:
                        args = json.loads(tc_data["arguments"])
                    except json.JSONDecodeError:
                        args = {}
                    tc = ToolCall(
                        id=tc_data["id"],
                        name=tc_data["name"],
                        arguments=args,
                    )
                    parsed_calls.append(tc)
                    tool_call_blocks.append({
                        "id": tc_data["id"],
                        "type": "function",
                        "function": {
                            "name": tc_data["name"],
                            "arguments": tc_data["arguments"],
                        },
                    })
                assistant_msg["tool_calls"] = tool_call_blocks
            messages.append(assistant_msg)

            if not parsed_calls:
                yield {"type": "done"}
                return

            # ── 执行工具 ──
            for tc in parsed_calls:
                result = await self._execute_tool_call(tc)
                yield {"type": "tool_result", "name": tc.name, "content": result}
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })

        raise DecisionError(
            f"超过最大迭代次数 ({self.max_iterations})，未得到最终回复"
        )

    # ── 内部：LLM 调用 ──────────────────────

    def _call_llm(self, messages: list[dict]) -> Decision:
        """调用 LLM 并解析响应中的 tool_calls。

        Args:
            messages: 对话消息列表

        Returns:
            Decision 对象

        Raises:
            DecisionError: LLM 调用失败
        """
        tools = self.registry.get_tools_schema()
        logger.debug(f"发送 LLM 请求，消息数: {len(messages)}，工具数: {len(tools)}")

        try:
            response = self.llm.client.chat.completions.create(
                model=self.llm.model,
                messages=messages,
                tools=tools,
            )
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            raise DecisionError(f"LLM 调用失败: {e}") from e

        choice = response.choices[0]
        msg = choice.message

        # 解析 tool_calls
        parsed_calls: list[ToolCall] = []
        if msg.tool_calls:
            for tc in msg.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {}
                parsed_calls.append(ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=args,
                ))

        # 将 assistant 消息追加回 messages（供下一轮 LLM 使用）
        assistant_msg: dict = {"role": "assistant"}
        if msg.content:
            assistant_msg["content"] = msg.content
        if msg.tool_calls:
            assistant_msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in msg.tool_calls
            ]
        messages.append(assistant_msg)

        decision = Decision(
            content=msg.content,
            tool_calls=parsed_calls,
            thought=msg.content if parsed_calls else None,
        )
        logger.debug(
            f"决策结果: is_final={decision.is_final}, "
            f"tool_calls={len(decision.tool_calls)}"
        )
        return decision

    # ── 内部：工具执行 ──────────────────────

    async def _execute_tool_call(self, tc: ToolCall) -> str:
        """执行单个工具调用并返回结果字符串。

        Args:
            tc: 工具调用信息

        Returns:
            工具执行结果（或错误信息）
        """
        logger.info(f"执行工具: {tc.name}({tc.arguments})")
        try:
            tool = self.registry.get(tc.name)
            result = await tool.execute(**tc.arguments)
            logger.debug(f"工具 {tc.name} 返回: {result[:100]}...")
            return result
        except ToolError:
            return f"错误：工具 '{tc.name}' 未注册"
        except Exception as e:
            logger.error(f"工具 {tc.name} 执行失败: {e}")
            return f"错误：工具 '{tc.name}' 执行失败 - {e}"