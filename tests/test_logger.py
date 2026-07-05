"""测试 Logger 模块"""

import os
from agent.logger import AgentLogger


def test_logger_creation():
    """验证 AgentLogger 可被创建并获取 logger."""
    logger = AgentLogger("test-module")
    assert logger.logger.name == "test-module"


def test_logger_handlers_exist():
    """验证创建后包含 console 和 file 两个 handler."""
    logger = AgentLogger("test-handlers")
    assert len(logger.logger.handlers) == 2


def test_logger_no_duplicate_handlers():
    """验证多次实例化不会重复添加 handler."""
    AgentLogger("test-dup")
    logger2 = AgentLogger("test-dup")
    assert len(logger2.logger.handlers) == 2


def test_log_file_created(tmp_path):
    """验证日志文件在指定目录中创建."""
    logger = AgentLogger("test-file")
    logger.info("测试一条日志")

    # 检查 logs 目录下是否有当天的日志文件
    from datetime import datetime
    log_dir = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "logs"
    )
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = os.path.join(log_dir, f"{today}.log")
    assert os.path.exists(log_file)
