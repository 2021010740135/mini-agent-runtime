# Mini Agent Runtime

从零实现的 AI Agent 运行时，不依赖任何 Agent 框架（LangChain/LangGraph/AutoGen 等），仅用 `openai` 库驱动 LLM。

## 快速复现

```bash
git clone https://github.com/2021010740135/mini-agent-runtime.git
cd mini-agent-runtime

# 配置 API Key
cp .env.example .env
# 编辑 .env 填入真实 API Key（默认 DeepSeek）

# 安装依赖
uv sync

# CLI 模式
uv run python main.py

# Web UI 模式（推荐：支持多 session 切换）
uv run streamlit run web/app.py

# 运行测试
uv run pytest tests/ -v
```

## 做了什么

**核心循环（ReAct 模式）**：用户输入 → LLM 判断 → 有工具则执行并回传结果 → 再问 LLM → 直到产生文本回复。

**4 个工具**：calculator（AST 安全计算）、search（mock 关键词匹配）、todo（session 级待办管理）、read_docs（文件读取+路径穿越防护）。通过 `ToolRegistry` 注册，LLM 基于 JSON Schema 自主决策调用。

**多 session 隔离**：同一用户可创建多个独立会话窗口，分别查天气记待办、写周报记待办，随时切换续聊互不影响。通过 `SessionManager` 按 `user_id/session_id` 以 JSON 文件持久化到 `data/sessions/`。

**上下文管理**：每轮对话前估算 token，超预算时自动压缩——保留最近 6 条消息不变，更早的消息合并为增量摘要。支持纯对话追问和带工具调用的追问。

**131 条测试**全部通过，覆盖所有模块。

## Memory 的召回时机与放置方式

| 时机 | 做了什么 |
|------|---------|
| **每次对话前** | 从 Session 加载完整消息历史，传入 ContextManager |
| **上下文超限时** | 滑动窗口：保留最近 6 条 + 其余压缩为摘要 |
| **工具调用后** | 工具执行结果追加到 messages，作为下一轮 LLM 输入 |
| **切换 session 时** | 从持久化的 `context_summary` 恢复历史压缩状态 |

消息放置顺序：`system prompt → 历史摘要(可选) → 最近 N 条消息 → 最新用户输入`

优先保留最近消息，因为细节对追问最重要；工具结果必须放入上下文，否则 LLM 不知道"刚才查到了什么"。

## 项目结构

```
mini-agent-runtime/
├── agent/                  # 核心：runtime、decision、memory、context、session 等
├── tools/                  # 工具：base、registry、calculator、mock_search、todo、read_docs
├── web/                    # Streamlit Web UI
├── tests/                  # 131 条测试
├── main.py                 # CLI 入口
└── .env.example            # 环境变量模板
```
