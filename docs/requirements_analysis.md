# 需求分析文档

> Mini Agent Runtime — 从零实现的 Agent 运行时（面试项目）

---

## 1. 项目背景

本项目是一个用于技术面试展示的 **mini-agent-runtime**，旨在从零实现一个轻量级的 AI Agent 运行时。

**核心约束：**
- 不允许使用 LangGraph、OpenHands、AutoGen、OpenClaw 等现成 Agent 框架
- 使用 Python 3.11+
- 允许使用 OpenAI-compatible Chat Completion API 与 LLM 通信
- 工具调用（Tool Calling）、决策循环（Agent Loop）、记忆管理、会话持久化均需自行实现

---

## 2. 功能需求

### 2.1 Agent 核心循环（F1）

- Agent 接收用户自然语言输入
- 通过 LLM 判断是否需要调用工具
- 如果需要，调用对应工具，将结果反馈给 LLM
- 如果不需要，直接返回最终回答
- 支持多轮工具调用（一次回答可能需要调用多个工具）

### 2.2 LLM 通信（F2）

- 封装 OpenAI-compatible Chat Completion API
- 支持 System Prompt、User Message、Assistant Message、Tool Call/Result 消息
- 支持流式输出（可选）
- 支持配置 API Key、Base URL、Model

### 2.3 决策引擎（F3）

- 解析 LLM 返回的 tool_calls，提取工具名和参数
- 区分"调用工具"和"返回最终答案"两种决策结果
- 处理 LLM 响应格式异常

### 2.4 工具系统（F4）

- 可插拔的工具基类（BaseTool），统一接口
- 工具注册中心（ToolRegistry），支持注册、查找、生成 tool schema
- 内置示例工具：计算器、模拟搜索、待办事项、文档读取

### 2.5 会话管理（F5）

- 每个会话有唯一 ID
- 会话内维护完整的消息历史
- 支持会话持久化到本地文件（JSON）
- 支持加载历史会话
- 支持同一用户同时拥有多个独立会话，例如窗口 1 用于天气和待办，窗口 2 用于周报和待办，两者上下文和工具状态互不影响
- 支持通过 `user_id + session_id` 定位会话；如果没有传入 `session_id`，系统应创建新会话并返回该 ID
- 支持列出指定用户的历史会话，便于用户选择继续某个窗口的上下文
- 会话数据应至少包含：`session_id`、`user_id`、创建时间、更新时间、消息历史、会话级工具状态
- 会话持久化格式使用 JSON，建议按用户和会话拆分存储，例如 `data/sessions/<user_id>/<session_id>.json`
- 会话恢复后，Agent 应继续使用该会话的消息历史、上下文摘要和会话级工具状态
- 会话隔离边界：一个会话内的用户输入、assistant 回复、tool_calls、tool results、上下文摘要、todo 等状态不得污染其他会话

### 2.6 记忆管理（F6）

- 短期记忆：当前会话的对话记录
- 长期记忆：跨会话的关键信息存储（可选实现）
- 上下文窗口控制：防止超长会话导致 token 超限
- 上下文摘要应归属于具体 session，不能作为全局摘要共享
- 每次调用 LLM 时，推荐传入：System Prompt、当前 session 的历史摘要、最近若干轮原始消息、当前用户输入、必要的工具调用结果
- 不建议把所有日志、无关 session 历史、跨窗口待办状态塞入当前上下文

### 2.7 日志系统（F7）

- 记录每次 LLM 调用的请求和响应
- 记录工具调用的输入和输出
- 日志按日期轮转，存储在 logs/ 目录

### 2.8 错误处理（F8）

- LLM 调用失败时的重试机制
- 工具执行异常时的优雅降级
- 决策解析失败时的容错处理

---

## 3. 非功能需求

| 需求 | 说明 |
|------|------|
| NFR1 可测试性 | 核心模块独立可测，使用 pytest 编写单元测试 |
| NFR2 可扩展性 | 新增工具只需继承 BaseTool 并注册即可 |
| NFR3 可观测性 | 日志完整记录 Agent 运行轨迹，便于调试和录屏展示 |
| NFR4 代码质量 | 类型标注（type hints）、模块化设计、单一职责 |
| NFR5 会话隔离 | 多个 session 之间的消息、摘要、工具状态必须隔离，避免交叉污染 |

---

## 4. 技术选型

| 组件 | 选型 | 理由 |
|------|------|------|
| 语言 | Python 3.11+ | 主流的 AI/ML 语言，生态丰富 |
| LLM SDK | openai | 官方库，兼容 OpenAI-compatible API |
| 配置管理 | python-dotenv | 环境变量加载，安全简便 |
| 数据校验 | pydantic v2 | 类型安全，工具参数校验 |
| 测试框架 | pytest | 简洁灵活，生态成熟 |

**明确不使用：** LangGraph、OpenHands、AutoGen、OpenClaw 或任何其他现成 Agent 框架。

---

## 5. 模块划分

```
agent/        → Agent 核心：运行时、LLM 客户端、决策、Prompt、上下文、会话、会话管理器、记忆、日志、异常
tools/        → 工具系统：基类、注册中心、计算器、搜索、待办事项、文档读取
tests/        → 单元测试，按模块拆分
docs/         → 项目文档
data/sessions/→ 会话持久化数据，建议按 user_id/session_id 拆分
logs/         → 运行日志
```

---

## 6. 多 Session 验收场景

以下场景用于验证 F5/F6 是否达标：

1. 用户 A 创建窗口 1，输入“帮我查天气，并把带伞加入待办”，系统返回 `session_id=s1`。
2. 用户 A 创建窗口 2，输入“帮我写周报，并把提交周报加入待办”，系统返回 `session_id=s2`。
3. 用户 A 回到窗口 1，继续问“刚才那个待办有哪些？”，Agent 只能看到窗口 1 的上下文和待办。
4. 用户 A 回到窗口 2，继续问“继续完善刚才的周报”，Agent 只能看到窗口 2 的上下文和待办。
5. 重启程序后，通过 `user_id=A, session_id=s1` 加载窗口 1，历史消息、摘要和待办状态应恢复。
6. `s1` 与 `s2` 的 JSON 文件、消息历史、上下文摘要、工具状态互不覆盖。

---

## 7. 验收标准

- [ ] `python main.py` 能启动交互式 Agent Loop
- [ ] 用户输入计算问题，Agent 能自主调用 CalculatorTool 并返回结果
- [ ] 用户输入搜索问题，Agent 能自主调用 MockSearchTool 并返回结果
- [ ] 多轮对话中上下文正确传递
- [ ] 同一用户可创建多个独立 session，并通过 session_id 继续任意一个会话
- [ ] 会话可保存和恢复，恢复后消息历史、上下文摘要和会话级工具状态保持一致
- [ ] 不同 session 的 todo、tool results、context summary 不会互相污染
- [ ] 多 session 管理有对应测试用例：创建、加载、保存、列表、隔离、恢复
- [ ] 所有 tests/ 下的测试用例通过
- [ ] 录屏可展示完整工作流程
