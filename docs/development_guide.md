# 开发指南

> Mini Agent Runtime 开发、测试、录屏与文档编写指南

---

## 1. 项目概述

本项目是一个从零实现的 **mini-agent-runtime**，用于技术面试展示。

**技术约束：**
- 使用 Python 3.11+
- 不允许使用 LangGraph、OpenHands、AutoGen、OpenClaw 等现成 Agent 框架
- 允许使用 OpenAI-compatible Chat Completion API（通过 `openai` 库）

---

## 2. 环境搭建

### 2.1 前提条件

- Python 3.11+
- pip

### 2.2 安装依赖

```bash
pip install -r requirements.txt
```

### 2.3 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入你的 API Key：

```
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
```

> 支持任何 OpenAI-compatible 的 API 端点（如 Azure OpenAI、本地 Ollama、DeepSeek 等），只需修改 `OPENAI_BASE_URL` 和 `LLM_MODEL`。

### 2.4 验证安装

```bash
python -c "from agent import AgentRuntime; from tools import BaseTool; print('OK')"
```

---

## 3. 项目结构

```
mini-agent-runtime/
├── main.py                 # 程序入口
├── requirements.txt        # Python 依赖
├── .env.example            # 环境变量模板
├── design_answers.md       # 面试设计问题回答
├── agent/                  # Agent 核心模块
│   ├── __init__.py
│   ├── runtime.py          # Agent 主循环控制器
│   ├── llm_client.py       # LLM API 封装
│   ├── decision.py         # 决策引擎（解析 LLM 输出）
│   ├── prompts.py          # Prompt 模板
│   ├── context.py          # 上下文管理
│   ├── session.py          # 单个会话数据模型
│   ├── session_manager.py  # 多 session 创建、加载、保存、列表与隔离
│   ├── memory.py           # 记忆管理
│   ├── logger.py           # 日志模块
│   └── errors.py           # 自定义异常
├── tools/                  # 工具模块
│   ├── __init__.py
│   ├── base.py             # 工具基类
│   ├── registry.py         # 工具注册中心
│   ├── calculator.py       # 计算器工具
│   ├── mock_search.py      # 模拟搜索工具
│   ├── todo.py             # 待办事项工具
│   └── read_docs.py        # 文档读取工具
├── docs/                   # 项目文档
│   ├── requirements_analysis.md
│   ├── development_guide.md
│   └── agent_notes.md
├── tests/                  # 单元测试
│   ├── test_calculator.py
│   ├── test_tool_registry.py
│   ├── test_session.py
│   ├── test_context.py
│   └── test_decision_parser.py
├── data/sessions/          # 会话持久化目录
└── logs/                   # 日志输出目录
```

---

## 4. 开发流程

### 4.1 推荐的实现顺序

**核心思路**：先把 Agent 主链路跑通（"用户输入 → LLM → 输出"），再逐步添加记忆、工具等外围能力。这样每个阶段都能看到可运行的成果，而不是到最后才串联。

已完成阶段：

| 阶段 | 模块 | 说明 |
|------|------|------|
| **阶段 1** | `agent/errors.py` | 定义异常类层级 ✅ |
| **阶段 2** | `agent/logger.py` | 日志记录器 ✅ |
| **阶段 3** | `tools/base.py` | 工具抽象基类 ✅ |

待实现阶段（按新顺序）：

| 阶段 | 模块 | 说明 |
|------|------|------|
| **阶段 4** | `agent/llm_client.py` | LLM API 封装——先把 LLM 调用跑通，能真正发请求并收到回复 |
| **阶段 5** | `agent/prompts.py` + `agent/runtime.py` | 组装主循环：「用户输入 → 构造消息 → 调 LLM → 输出回复」 |
| **阶段 6** | `agent/session.py` + `agent/session_manager.py` + `agent/memory.py` | 实现多 session 管理：创建、加载、保存、列表、恢复，并保证不同窗口上下文隔离 |
| **阶段 7** | `agent/context.py` | 管理上下文窗口，防止 token 超限 |
| **阶段 8** | `tools/registry.py` + `tools/base.py` | 完善工具注册中心（依赖注入 Logger） |
| **阶段 9** | 各工具实现 | `calculator.py` → `mock_search.py` → `todo.py` → `read_docs.py` |
| **阶段 10** | `agent/decision.py` | 决策引擎——让 Agent 学会解析 LLM 输出，自主调用工具 |

### 4.2 编码规范

- 所有函数和类方法必须标注类型（type hints）
- 使用 `dataclass` 定义数据模型
- 每个模块职责单一，边界清晰
- 对外接口通过 `__init__.py` 统一导出
- 避免模块间循环依赖
- 注释和文档字符串使用中文

### 4.3 关键设计原则

1. **依赖方向**：`runtime` → `llm_client` / `decision` / `tools`，`tools` 不依赖 `agent`
2. **工具可插拔**：新增工具只需继承 `BaseTool`，实现 `execute()`，注册到 `ToolRegistry`
3. **LLM 解耦**：`LLMClient` 封装所有 API 细节，其他模块不直接接触 `openai` 库
4. **决策独立**：`DecisionEngine` 解析 LLM 原始输出为结构化决策，屏蔽格式变化
5. **会话隔离**：Runtime 接收 `user_id/session_id` 后只加载该 session 的消息历史、上下文摘要和工具状态，不读取其他 session 的状态
6. **状态归属明确**：全局组件负责无状态能力，session 组件负责消息、摘要、待办等会话级状态

### 4.4 多 Session 实现约定

建议新增 `agent/session_manager.py`，职责如下：

- `create_session(user_id: str) -> Session`：创建新 session，并返回唯一 `session_id`
- `get_session(user_id: str, session_id: str) -> Session`：加载已有 session；不存在时抛出明确异常
- `save_session(session: Session) -> None`：将 session 写入 JSON 文件
- `list_sessions(user_id: str) -> list[SessionMeta]`：列出指定用户的历史 session 元信息
- `delete_session(user_id: str, session_id: str) -> None`：可选，用于清理测试或演示数据

推荐持久化路径：

```text
data/sessions/<user_id>/<session_id>.json
```

推荐 JSON 字段：

```json
{
  "session_id": "...",
  "user_id": "...",
  "created_at": "2026-07-05T10:00:00",
  "updated_at": "2026-07-05T10:05:00",
  "messages": [],
  "context_summary": "",
  "tool_state": {
    "todo": []
  }
}
```

`AgentRuntime.run_once()` 建议改为接收 `user_input`、`user_id`、`session_id`。如果 `session_id` 为空则创建新 session；如果存在则加载该 session。一次交互结束后保存 session。

---

## 5. 测试指南

### 5.1 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行单个测试文件
pytest tests/test_calculator.py -v

# 带覆盖率报告
pytest tests/ -v --cov=agent --cov=tools --cov-report=term-missing
```

### 5.2 测试要求

- 每个核心模块至少有一个基础测试用例
- 工具模块测试应覆盖：实例化、execute() 调用、异常处理
- Agent 核心模块测试可使用 mock 隔离 LLM 依赖
- 多 session 测试必须覆盖：创建两个 session、分别写入消息、分别写入 todo 状态、保存、重新加载、确认互不污染
- session 持久化测试应使用 pytest 的 `tmp_path`，避免污染真实 `data/sessions/` 目录
- 测试文件命名：`test_<module>.py`
- 测试函数命名：`test_<功能描述>`

### 5.3 当前测试用例

| 测试文件 | 覆盖模块 | 测试点 |
|----------|----------|--------|
| `test_calculator.py` | CalculatorTool | 工具实例化、name 属性 |
| `test_tool_registry.py` | ToolRegistry | 注册表初始化 |
| `test_session.py` | Session | session_id 自动生成、消息追加、拷贝读取 |
| `test_session_manager.py` | SessionManager | 创建、保存、加载、列表、多 session 隔离、恢复 |
| `test_context.py` | ContextManager | max_tokens 配置 |
| `test_decision_parser.py` | DecisionEngine | 引擎实例化 |

---

## 6. 录屏指南

录屏是面试展示的重要环节，建议按以下流程准备：

### 6.1 录屏前准备

- [ ] 确认 `.env` 配置正确，API 可正常调用
- [ ] 确认 `pytest tests/ -v` 全部通过
- [ ] 清理 `logs/` 目录，确保日志从零开始
- [ ] 准备 3-5 个有代表性的测试输入

### 6.2 建议演示内容

1. **项目结构概览**（30 秒）：简要介绍目录结构和核心模块
2. **启动 Agent**（1 分钟）：运行 `python main.py`，展示交互式对话
3. **工具调用演示**（2 分钟）：
   - 输入计算问题 → Agent 调用 CalculatorTool
   - 输入搜索问题 → Agent 调用 MockSearchTool
   - 展示多轮工具链式调用
4. **多 Session 与持久化**（45 秒）：创建窗口 1/窗口 2，展示两个 session 文件和互不影响的上下文/待办状态
5. **运行测试**（30 秒）：`pytest tests/ -v` 展示全部通过
6. **代码亮点**（1 分钟）：挑选 2-3 个设计亮点讲解

### 6.3 录屏工具建议

- Windows: OBS Studio / Xbox Game Bar（Win+G）
- macOS: QuickTime Player / OBS Studio
- Linux: OBS Studio / SimpleScreenRecorder

---

## 7. README 编写指南

README.md 是面试官的第一印象，建议突出以下内容：

### 7.1 必须包含

- [ ] **一句话定位**：这是什么项目（如"从零实现的 AI Agent 运行时"）
- [ ] **架构图**（Mermaid 或 ASCII）：Agent Loop 流程图
- [ ] **快速开始**：3 步跑起来
- [ ] **核心亮点**：3-5 条，展示技术深度
- [ ] **项目结构**：目录树 + 简要说明
- [ ] **运行测试**：pytest 命令

### 7.2 建议内容

```markdown
# Mini Agent Runtime

> 从零实现的 AI Agent 运行时，不依赖任何 Agent 框架

## 架构概览

[Mermaid 流程图：用户输入 → Runtime → LLM → Decision → Tool → 循环 → 输出]

## 核心亮点

- 自行实现 Agent Loop，而非调用框架
- 可插拔工具系统，支持 Tool Schema 自动生成
- 流式 LLM 调用支持
- 完整的内存与会话管理
- 100% 类型标注

## 快速开始

...

## 技术栈

- Python 3.11+
- OpenAI-compatible API
- 零 Agent 框架依赖

## 运行测试

pytest tests/ -v
```

---

## 8. 常见问题

### Q: 为什么不使用 LangGraph 等框架？

**A:** 这是面试项目的核心考察点。面试官希望通过"从零实现"来考察候选人对 Agent 架构的底层理解——包括 Agent Loop、Tool Calling 协议、上下文管理、决策解析等。使用框架会掩盖这些理解。

### Q: 如何切换不同的 LLM？

**A:** 修改 `.env` 中的 `OPENAI_BASE_URL` 和 `LLM_MODEL` 即可。任何兼容 OpenAI Chat Completion API 的服务（DeepSeek、通义千问、Ollama 本地模型等）均可直接使用。

### Q: 工具调用失败如何处理？

**A:** 分层处理——
1. 工具内部 catch 异常，返回错误信息给 LLM
2. DecisionEngine 检测到连续失败时触发降级策略
3. Runtime 设置最大重试次数，超限后返回友好提示

---

## 9. 参考资料

- [OpenAI Chat Completions API](https://platform.openai.com/docs/guides/function-calling)
- [Pydantic v2 文档](https://docs.pydantic.dev/latest/)
- [pytest 官方文档](https://docs.pytest.org/)
