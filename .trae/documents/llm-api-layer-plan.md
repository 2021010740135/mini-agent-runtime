# LLM API 调用层 — 位置分析与实现计划

## 摘要

用户询问「LLM API 调用层」应该放在项目中的哪个位置。经过代码探索，该层对应的文件 **`agent/llm_client.py`** 已经存在于正确的位置，无需新增目录。本文档说明为什么这个位置是合理的，以及它与其他模块的关系和后续实现要点。

---

## 当前状态分析

### 已有文件

[agent/llm_client.py](file:///d:/code/mini-agent-runtime/agent/llm_client.py) 是一个骨架文件：

```python
"""LLM 客户端——封装 OpenAI-compatible Chat Completion API"""

class LLMClient:
    """与 LLM 服务通信的客户端."""

    def __init__(self) -> None:
        pass
```

### 它在依赖图中的位置

来自 [development_guide.md](file:///d:/code/mini-agent-runtime/docs/development_guide.md#L128-L130) 的设计原则：

```
AgentRuntime (runtime.py)
  ├── 使用 LLMClient (llm_client.py)   ← 调用 LLM
  ├── 使用 DecisionEngine (decision.py) ← 解析 LLM 输出
  └── 使用 ToolRegistry (tools/)        ← 派发工具调用

tools/ 不依赖 agent/  ← 已在当前代码中成立
```

### 为什么 llm_client.py 放在 agent/ 下是正确的

1. **语义归属明确**：LLM 客户端是 Agent 核心运行时的一部分，不是通用工具。
2. **依赖方向合理**：它被 `runtime.py` 引用，不需要被 `tools/` 引用（tools 不依赖 agent）。
3. **与 `decision.py` 配套**：LLM 客户端产出原始响应 → DecisionEngine 解析响应。两者紧密协作，放在同一包中合理。
4. **未来不会膨胀**：LLM 调用是单一职责模块，封装 `openai` 库 + 重试 + 流式等，不需要子目录。

### 什么时候需要考虑拆分？

如果未来出现以下情况，可以重构为子包 `agent/llm/`：
- 需要支持多种 LLM Provider（OpenAI、Anthropic Claude、本地 Ollama 等），每种 Provider 需要独立文件。
- 需要独立的 Token 计数器、速率限制器、缓存层等。

**当前阶段不需要**，`agent/llm_client.py` 单文件足够。

---

## 实现计划（阶段 6，按 development_guide.md 的 13 阶段顺序）

`agent/llm_client.py` 的推荐实现顺序在 development_guide 中排第 6 阶段：
1. ~~errors.py~~ ✅
2. ~~logger.py~~ (骨架已存在)
3. ~~tools/base.py~~ ✅
4. ~~tools/registry.py~~ (骨架已存在)
5. ~~各工具实现~~ (骨架已存在)
6. **`agent/llm_client.py`** ← **当前阶段**

### llm_client.py 应实现的内容

遵循 `development_guide.md` 中的编码规范（类型标注、中文文档字符串、单一职责）：

| 功能点 | 说明 |
|--------|------|
| `__init__(self, api_key, base_url, model)` | 加载配置，创建 `openai.AsyncOpenAI` 客户端 |
| `async chat(self, messages, tools=None)` | 发送消息到 LLM，返回原始响应对象 |
| 重试逻辑 | LLM 调用失败时以指数退避重试（抛出 `LLMError`） |
| 可选：`async chat_stream()` | 流式输出支持 |
| 不承担职责 | 不解析 tool_calls（这是 `DecisionEngine` 的职责），不维护上下文（`ContextManager`），不记录日志（`AgentLogger`） |

### 伪代码结构

```python
"""LLM 客户端——封装 OpenAI-compatible Chat Completion API"""

from openai import AsyncOpenAI
from .errors import LLMError


class LLMClient:
    """与 LLM 服务通信的客户端."""

    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        self.model = model
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def chat(self, messages: list[dict], tools: list[dict] | None = None):
        """发送对话请求，返回 LLM 原始响应."""
        pass
```

---

## 结论

- **不需要新增文件或目录**。LLM API 调用层就是 `agent/llm_client.py`，位置合理。
- **不需要修改其他文件**来适配这个设计（现有 `agent/__init__.py` 已导出 `AgentRuntime`，`runtime.py` 将来 import `LLMClient` 即可）。
- 按 `development_guide.md` 阶段 6 推进实现即可。

---

## 验证步骤

1. `uv run python -c "from agent.llm_client import LLMClient; print('import OK')"` — 导入验证
2. `uv run pytest tests/ -v` — 确保不破坏已有测试
3. 编写 `tests/test_llm_client.py`（可选，如果需要 mock LLM 响应）
