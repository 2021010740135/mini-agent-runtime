"""测试 ReadDocs 工具"""

import os
import tempfile

import pytest

from tools.read_docs import ReadDocsTool


@pytest.fixture
def tmp_dir():
    """创建临时目录作为 base_dir."""
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def tool(tmp_dir):
    return ReadDocsTool(base_dir=tmp_dir)


# ── 基本读取 ──

@pytest.mark.asyncio
async def test_read_existing_file(tmp_dir, tool):
    """验证读取存在的文本文件，返回带行号的内容."""
    file_path = os.path.join(tmp_dir, "test.txt")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("第一行\n第二行\n第三行")

    result = await tool.execute(file_path="test.txt")
    assert "   1  第一行" in result
    assert "   2  第二行" in result
    assert "   3  第三行" in result


@pytest.mark.asyncio
async def test_read_single_line(tmp_dir, tool):
    """验证读取单行文件."""
    file_path = os.path.join(tmp_dir, "single.txt")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("只有一行")

    result = await tool.execute(file_path="single.txt")
    assert "   1  只有一行" in result


# ── 错误处理 ──

@pytest.mark.asyncio
async def test_empty_file_path(tool):
    """验证空路径返回错误."""
    result = await tool.execute(file_path="")
    assert "不能为空" in result


@pytest.mark.asyncio
async def test_file_not_found(tool):
    """验证文件不存在返回错误."""
    result = await tool.execute(file_path="nonexistent.txt")
    assert "文件不存在" in result


@pytest.mark.asyncio
async def test_path_traversal_blocked(tmp_dir, tool):
    """验证路径穿越 ../ 被阻断."""
    result = await tool.execute(file_path="../etc/passwd")
    assert "不允许" in result


@pytest.mark.asyncio
async def test_empty_file(tmp_dir, tool):
    """验证空文件返回空提示."""
    file_path = os.path.join(tmp_dir, "empty.txt")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("")

    result = await tool.execute(file_path="empty.txt")
    assert "内容为空" in result


# ── schema ──

def test_to_openai_schema(tool):
    schema = tool.to_openai_schema()
    assert schema["type"] == "function"
    assert schema["function"]["name"] == "read_docs"
    assert "file_path" in schema["function"]["parameters"]["properties"]
    assert schema["function"]["parameters"]["required"] == ["file_path"]


# ── 读取真实项目文件（测试资源文件） ──

@pytest.mark.asyncio
async def test_read_real_project_file():
    """验证以当前目录为 base_dir 读取项目真实文件."""
    tool = ReadDocsTool()  # 默认 base_dir=os.getcwd()
    result = await tool.execute(file_path="README.md")
    assert "agent runtime" in result.lower()
    # 确认有行号
    assert "   1" in result