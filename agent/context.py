"""上下文管理——Token 估算、分块摘要、滑动窗口、增量压缩"""

import logging

logger = logging.getLogger("mini-agent")


class ContextManager:
    """上下文窗口管理器.

    解决两大问题：
    ┌──────────────────────┬─────────────────────┬─────────────────────────┐
    │ 问题                 │ 场景                │ 方案                    │
    ├──────────────────────┼─────────────────────┼─────────────────────────┤
    │ 首轮长输入 TTFT 过高 │ 用户粘贴 5000 字文档 │ chunk_and_summarize()   │
    │ 多轮对话 token 溢出  │ 200 轮对话          │ optimize() 增量压缩     │
    └──────────────────────┴─────────────────────┴─────────────────────────┘

    压缩策略：
    - 滑动窗口：保留最近 keep_recent 条消息原文
    - 增量压缩：旧摘要 + 新溢出 → 合并摘要（避免全量重压膨胀）
    - 分块摘要：超长单条消息切块后逐块摘要再合并
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

    # ═══════════════════════════════════════════════════
    # Token 估算
    # ═══════════════════════════════════════════════════

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

    # ═══════════════════════════════════════════════════
    # 场景 1：首轮长输入 → 分块摘要
    # ═══════════════════════════════════════════════════

    @staticmethod
    def chunk_and_summarize(
        text: str,
        llm_client,
        chunk_size: int = 2000,
    ) -> str:
        """处理超长单条消息：分块 → 逐块摘要 → 合并为总摘要.

        适用场景：用户在第一条消息中粘贴了很长的文档。
        效果：将主 LLM 调用的输入从 5000+ token 降至 ~300 token，
               TTFT 从 5-10s 稳定压缩到 2s 以内。

        Args:
            text: 超长文本
            llm_client: 用于生成摘要的 LLM 客户端
            chunk_size: 每块的字符数上限

        Returns:
            合并后的总摘要文本，可直接作为消息内容发送给主 LLM
        """
        if len(text) <= chunk_size:
            return text

        # 第一步：切块
        chunks = [
            text[i : i + chunk_size]
            for i in range(0, len(text), chunk_size)
        ]
        logger.info(
            f"chunk_and_summarize: 文本长度 {len(text)} → "
            f"{len(chunks)} 块，每块 ≤ {chunk_size} 字符"
        )

        # 第二步：逐块摘要
        sub_summaries: list[str] = []
        for idx, chunk in enumerate(chunks, 1):
            try:
                summary = llm_client.chat(
                    [
                        {
                            "role": "system",
                            "content": "请用 100 字以内概括以下内容的核心要点。",
                        },
                        {"role": "user", "content": chunk},
                    ],
                    temperature=0.3,
                    max_tokens=200,
                )
                sub_summaries.append(summary)
                logger.debug(f"  块 {idx}/{len(chunks)} 摘要完成")
            except Exception as e:
                logger.warning(f"  块 {idx} 摘要失败: {e}，使用截断")
                sub_summaries.append(chunk[:100] + "...")

        if len(sub_summaries) == 1:
            return sub_summaries[0]

        # 第三步：合并子摘要
        try:
            merged = llm_client.chat(
                [
                    {
                        "role": "system",
                        "content": (
                            "请将以下多段摘要合并为一段连贯的总结（300 字以内），"
                            "保留关键信息和逻辑关系。"
                        ),
                    },
                    {"role": "user", "content": "\n---\n".join(sub_summaries)},
                ],
                temperature=0.3,
                max_tokens=500,
            )
            logger.info(
                f"chunk_and_summarize 完成: {len(chunks)} 块 → 1 条总摘要"
            )
            return merged
        except Exception as e:
            logger.warning(f"合并摘要失败: {e}，返回拼接结果")
            return "\n".join(sub_summaries)

    # ═══════════════════════════════════════════════════
    # 场景 2：多轮对话溢出 → 增量压缩 + 滑动窗口
    # ═══════════════════════════════════════════════════

    def optimize(
        self,
        system_prompt: str,
        messages: list[dict],
    ) -> list[dict]:
        """优化消息列表，确保不超出 token 预算.

        策略：
        1. 未超限 → 直接返回 [system] + messages
        2. 已超限 → 增量压缩：只摘要新增溢出，与已有摘要合并
           + 滑动窗口保留最近 keep_recent 条原文

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

        # 增量压缩：只摘要溢出部分，与已有摘要合并
        if overflow and self.llm:
            try:
                new_part = self._summarize_batch(overflow)
                self._summary = self._merge_summaries(
                    existing=self._summary,
                    new_part=new_part,
                )
                logger.info(
                    f"增量压缩完成: +{len(overflow)} 条 → "
                    f"摘要长度 {len(self._summary)} 字符"
                )
            except Exception as e:
                logger.error(f"压缩失败: {e}")
                if not self._summary:
                    # 无已有摘要时使用降级策略
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

    # ═══════════════════════════════════════════════════
    # 内部：摘要生成与合并
    # ═══════════════════════════════════════════════════

    def _summarize_batch(self, messages: list[dict]) -> str:
        """将一批消息压缩为一段摘要（不涉及已有摘要）."""
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

        assert self.llm is not None
        return self.llm.chat(summary_request, temperature=0.3, max_tokens=500)

    def _merge_summaries(self, existing: str, new_part: str) -> str:
        """将已有摘要与新摘要合并为一段连贯的摘要.

        增量压缩的核心——只处理新增部分，摘要不会随轮数膨胀。

        Args:
            existing: 已有累积摘要（可能为空字符串）
            new_part: 新增摘要

        Returns:
            合并后的统一摘要
        """
        if not existing:
            return new_part

        if not new_part:
            return existing

        assert self.llm is not None

        merge_request = [
            {
                "role": "system",
                "content": (
                    "你是一个摘要合并助手。请将以下两段对话摘要合并为一段"
                    "简洁连贯的摘要（200 字以内）。已有摘要在前，新增内容在后。"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"# 已有摘要\n{existing}\n\n"
                    f"# 新增内容\n{new_part}\n\n"
                    f"请合并为一段 200 字以内的摘要："
                ),
            },
        ]

        return self.llm.chat(merge_request, temperature=0.3, max_tokens=500)

    def _truncation_summary(self, messages: list[dict]) -> str:
        """降级策略：LLM 不可用时，取首尾各一条消息作为摘要."""
        if len(messages) <= 2:
            return f"(共 {len(messages)} 条历史消息)"
        first = messages[0]
        last = messages[-1]
        return (
            f"[共 {len(messages)} 条历史消息已省略] "
            f"最早话题: {first['content'][:80]}... | "
            f"最近话题: {last['content'][:80]}..."
        )

    # ═══════════════════════════════════════════════════
    # 状态管理
    # ═══════════════════════════════════════════════════

    @property
    def summary(self) -> str:
        """获取当前累积的摘要文本."""
        return self._summary

    def set_summary(self, summary: str) -> None:
        """恢复当前 session 的上下文摘要."""
        self._summary = summary or ""

    def clear(self) -> None:
        """清空摘要状态."""
        self._summary = ""
