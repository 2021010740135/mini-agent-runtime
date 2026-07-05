"""上下文管理——Token 估算、滑动窗口、摘要压缩"""

import logging

logger = logging.getLogger("mini-agent")


class ContextManager:
    """上下文窗口管理器.

    解决的问题：
    1. 首轮长输入导致 first token 延迟 → Token 预估 + 截断预警
    2. 长对话导致 token 超限 → 滑动窗口 + LLM 摘要压缩

    压缩策略：
    - 保留最近 keep_recent 条消息原文（滑动窗口）
    - 超出部分调用 LLM 压缩为一段摘要
    - 摘要作为 system 消息插入上下文顶部
    """

    def __init__(
        self,
        max_tokens: int = 4000,
        keep_recent: int = 6,
        llm_client=None,
    ) -> None:
        """初始化上下文管理器.

        Args:
            max_tokens: 上下文窗口的 token 预算上限
            keep_recent: 滑动窗口大小——保留最近 N 条消息不压缩
            llm_client: LLM 客户端，用于生成摘要（为 None 时使用降级策略）
        """
        self.max_tokens = max_tokens
        self.keep_recent = keep_recent
        self.llm = llm_client
        self._summary: str = ""

    # ─── Token 估算 ─────────────────────────────────────

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """估算单段文本的 token 数量.

        中英文混合粗略估算：
        - 中文：约 1.5~2 字符/token
        - 英文：约 4 字符/token
        - 这里取 2 字符/token（保守估计，留有余量）
        """
        return max(1, len(text) // 2)

    @staticmethod
    def estimate_tokens_batch(messages: list[dict]) -> int:
        """估算消息列表的总 token 数."""
        return sum(
            ContextManager.estimate_tokens(m.get("content", ""))
            for m in messages
        )

    def should_compress(self, messages: list[dict]) -> bool:
        """判断消息列表是否超出 token 预算."""
        total = self.estimate_tokens_batch(messages)
        return total > self.max_tokens

    # ─── 核心优化入口 ───────────────────────────────────

    def optimize(
        self,
        system_prompt: str,
        messages: list[dict],
    ) -> list[dict]:
        """优化消息列表，确保不超出 token 预算.

        策略：
        1. 未超限 → 直接返回 [system] + messages
        2. 已超限 → 旧消息压缩为摘要 + 最近 keep_recent 条原文

        Args:
            system_prompt: 系统提示词
            messages: 完整对话历史（不含 system prompt）

        Returns:
            可直接传给 LLMClient.chat() 的消息列表
        """
        total = self.estimate_tokens_batch(messages)
        total += self.estimate_tokens(system_prompt)

        if total <= self.max_tokens:
            return [{"role": "system", "content": system_prompt}] + messages

        logger.warning(
            f"上下文 token 超限（≈{total}/{self.max_tokens}），"
            f"触发压缩，当前消息数: {len(messages)}"
        )

        # 滑动窗口：最近 keep_recent 条保留原文
        if len(messages) <= self.keep_recent:
            keep = messages
            overflow = []
        else:
            keep = messages[-self.keep_recent:]
            overflow = messages[:-self.keep_recent]

        # 压缩溢出部分：优先 LLM 摘要，降级为简单截断
        if overflow and self.llm:
            try:
                self._summary = self._generate_llm_summary(overflow)
                logger.info(f"LLM 摘要生成成功，压缩 {len(overflow)} → 1 条摘要")
            except Exception as e:
                logger.error(f"LLM 摘要失败: {e}，降级为截断")
                self._summary = self._truncation_summary(overflow)
        elif overflow:
            self._summary = self._truncation_summary(overflow)

        # 组装最终结果
        result: list[dict] = [
            {"role": "system", "content": system_prompt},
        ]
        if self._summary:
            result.append({
                "role": "system",
                "content": f"[对话历史摘要]\n{self._summary}",
            })
        result.extend(keep)

        final_tokens = self.estimate_tokens_batch(result)
        logger.info(
            f"压缩完成: {len(messages)} 条消息 → {len(keep)} 条原文 + 摘要，"
            f"≈{total} tokens → ≈{final_tokens} tokens"
        )
        return result

    # ─── 摘要生成策略 ───────────────────────────────────

    def _generate_llm_summary(self, messages: list[dict]) -> str:
        """调用 LLM 将消息列表压缩为一段摘要.

        这是推荐策略——LLM 天然擅长理解和总结对话。
        压缩后从 5-10 秒首 token 延迟可降到 2 秒以内。
        """
        conversation_lines: list[str] = []
        for m in messages:
            speaker = "用户" if m["role"] == "user" else "AI"
            conversation_lines.append(f"{speaker}: {m['content']}")

        conversation = "\n".join(conversation_lines)
        summary_request = [
            {
                "role": "system",
                "content": (
                    "你是一个对话摘要助手。请将以下对话历史压缩为一段简洁的摘要"
                    "（200 字以内），只保留：关键话题、重要决策、用户偏好、"
                    "未完成的任务。忽略寒暄和重复内容。"
                ),
            },
            {"role": "user", "content": f"请摘要以下对话：\n{conversation}"},
        ]

        assert self.llm is not None  # 调用方保证
        return self.llm.chat(summary_request, temperature=0.3, max_tokens=500)

    def _truncation_summary(self, messages: list[dict]) -> str:
        """降级策略：LLM 不可用时，取首尾各一条消息作为摘要.

        虽然信息量有限，但能保证核心链路不中断。
        """
        if len(messages) <= 2:
            return f"(共 {len(messages)} 条历史消息)"
        first = messages[0]
        last = messages[-1]
        return (
            f"[共 {len(messages)} 条历史消息已省略] "
            f"最早话题: {first['content'][:80]}... | "
            f"最近话题: {last['content'][:80]}..."
        )

    # ─── 状态管理 ─────────────────────────────────────

    @property
    def summary(self) -> str:
        """获取当前累积的摘要文本."""
        return self._summary

    def clear(self) -> None:
        """清空摘要状态."""
        self._summary = ""