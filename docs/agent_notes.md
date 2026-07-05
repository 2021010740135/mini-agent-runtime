# Agent Notes

> 设计思路和技术决策记录，用于面试回顾

---

## 1. LLMClient 设计

### 依赖注入
`LLMClient` 不直接读 `.env`，而是由外部传入 `api_key`、`base_url`、`model`。好处：
- 测试时可以直接传假参数，不需要真实配置
- 同一进程内可以创建多个指向不同 LLM 的客户端

### 异常封装
所有 `openai` 底层异常统一转为 `LLMError`，上层代码只需 `except LLMError`。

---

## 2. ContextManager：上下文窗口管理

### 两个核心问题

| 问题 | 场景 | 解决方案 | 对应方法 |
|------|------|---------|---------|
| 首轮长输入 first token 慢 | 用户粘贴一篇 5000 字文档 | 分块摘要（chunk → 逐块摘要 → 合并） | `chunk_and_summarize()` |
| 200 轮对话 context 溢出 | 长对话 token 超限 | 增量压缩（旧摘要 + 新溢出 → 合并）+ 滑动窗口 | `optimize()` |

### First Token 延迟（TTFT = Time To First Token）

**定义**：从请求发出到 LLM 返回第一个字符的时间间隔。

**根因**：Transformer 的注意力机制复杂度是 O(n²)，输入长度翻倍 ≈ 首 token 延迟翻 4 倍。

**我们的方案**不是把长文本直接塞给 LLM，而是：
1. 将长文本切成多个小块
2. 逐块让 LLM 生成子摘要（每次调用 `max_tokens=200`，很快）
3. 将所有子摘要合并为总摘要
4. 只把总摘要发给主 LLM

这样主调用的输入从 5000+ token 降到 300 token 摘要，TTFT 从 5-10s 稳定压缩到 2s 以内。

### 增量压缩 vs 全量重压

**错误做法（全量重压）**：
```
每轮溢出 → 把所有溢出的历史消息重新摘要一遍
  摘要内容越来越长："讨论了 A、B、C、D、E、F、G..."
```

**正确做法（增量压缩）**：
```
第 10 轮溢出 → 摘要 = compress(msg[0:10])
第 20 轮溢出 → 摘要 = merge(旧摘要, compress(msg[10:20]))
  摘要始终控制在 200 字左右，不膨胀
```

代码对应：`_merge_summaries(existing_summary, new_summary)`。

### 摘要插入位置

摘要以 `[对话历史摘要]` 前缀插入到 system 消息层级，LLM 会将其视为权威背景知识。每次 `optimize()` 都重新构造 result 列表，所以摘要始终只有 1 条，不会堆积。

---

## 3. 开发过程中遇到的坑点

### 浅拷贝陷阱
`list.copy()` 只复制外层列表，内层 dict 仍是同一引用。
- 修复：`copy.deepcopy()`。
- 影响范围：`Session.get_messages()`。

### Token 阈值设置
单元测试中 `max_tokens` 必须小于测试数据的实际 token 数，否则压缩分支不会触发。
- 教训：测试阈值要比数据小，确保覆盖异常路径。

### 同名函数覆盖
Python 中同名函数静默覆盖，pytest 只运行最后一个。
- 教训：粘贴代码后检查是否有重复定义。

### max_tokens 预算需留余量
摘要本身、`[对话历史摘要]\n` 前缀、system prompt 都占 token。
- 建议：`估算值 * 0.8` 作为实际预警线。

### 首轮长输入 ≠ 多轮溢出
两种场景需要两套不同策略：
- **单条消息过长** → `chunk_and_summarize()` 分块摘要
- **历史消息过多** → `optimize()` 增量压缩 + 滑动窗口

---

## 4. 架构决策

| 决策 | 理由 |
|------|------|
| 依赖注入（Config → LLMClient） | 可测试、可替换 |
| Logger 双重输出（控制台 + 文件） | 用户可观察 + 排查可追溯 |
| MemoryStore 全量存储 + ContextManager 按需压缩 | 存储层不关心上下文策略，解耦 |
| 摘要降级兜底（`_truncation_summary`） | LLM 不可用时核心链路不中断 |
