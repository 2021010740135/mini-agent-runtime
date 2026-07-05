"""测试 Todo 工具"""

import pytest

from tools.todo import TodoTool


@pytest.fixture
def tool():
    return TodoTool()


# ── add ──

@pytest.mark.asyncio
async def test_add_task(tool):
    result = await tool.execute(action="add", task="学习 Python")
    assert "已添加任务 #1" in result
    assert "学习 Python" in result


@pytest.mark.asyncio
async def test_add_multiple_tasks(tool):
    await tool.execute(action="add", task="任务A")
    await tool.execute(action="add", task="任务B")
    await tool.execute(action="add", task="任务C")
    result = await tool.execute(action="list", task="")
    assert "任务A" in result
    assert "任务B" in result
    assert "任务C" in result


@pytest.mark.asyncio
async def test_add_empty_task(tool):
    result = await tool.execute(action="add", task="")
    assert "不能为空" in result


# ── list ──

@pytest.mark.asyncio
async def test_list_empty(tool):
    result = await tool.execute(action="list", task="")
    assert "待办列表为空" in result


@pytest.mark.asyncio
async def test_list_with_tasks(tool):
    await tool.execute(action="add", task="写代码")
    await tool.execute(action="add", task="写测试")
    result = await tool.execute(action="list", task="")
    assert "待办列表（共 2 项）" in result
    assert "写代码" in result
    assert "写测试" in result
    assert "[ ]" in result  # 未完成标记


# ── done ──

@pytest.mark.asyncio
async def test_done_task(tool):
    await tool.execute(action="add", task="完成任务")
    result = await tool.execute(action="done", task="1")
    assert "已标记任务 #1 为完成" in result
    # 确认列表中显示为完成
    list_result = await tool.execute(action="list", task="")
    assert "[x]" in list_result


@pytest.mark.asyncio
async def test_done_nonexistent_number(tool):
    result = await tool.execute(action="done", task="99")
    assert "不存在" in result


@pytest.mark.asyncio
async def test_done_non_numeric(tool):
    await tool.execute(action="add", task="测试")
    result = await tool.execute(action="done", task="abc")
    assert "不是有效的任务编号" in result


@pytest.mark.asyncio
async def test_done_empty_task_param(tool):
    await tool.execute(action="add", task="测试")
    result = await tool.execute(action="done", task="")
    assert "请提供任务编号" in result


# ── clear ──

@pytest.mark.asyncio
async def test_clear(tool):
    await tool.execute(action="add", task="任务1")
    await tool.execute(action="add", task="任务2")
    result = await tool.execute(action="clear", task="")
    assert "已清空全部 2 项任务" in result
    # 确认清空后列表为空
    list_result = await tool.execute(action="list", task="")
    assert "待办列表为空" in list_result


@pytest.mark.asyncio
async def test_clear_empty(tool):
    result = await tool.execute(action="clear", task="")
    assert "已清空全部 0 项任务" in result


# ── 错误 action ──

@pytest.mark.asyncio
async def test_invalid_action(tool):
    result = await tool.execute(action="delete", task="1")
    assert "不支持的操作" in result


# ── schema ──

def test_to_openai_schema(tool):
    schema = tool.to_openai_schema()
    assert schema["type"] == "function"
    assert schema["function"]["name"] == "todo"
    props = schema["function"]["parameters"]["properties"]
    assert "action" in props
    assert props["action"]["enum"] == ["add", "list", "done", "clear"]
    assert "task" in props
    assert schema["function"]["parameters"]["required"] == ["action"]