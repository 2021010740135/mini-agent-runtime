"""日志模块——统一的日志记录"""

import logging


class AgentLogger:
    """Agent 专用日志记录器."""

    def __init__(self, name: str = "mini-agent") -> None:
        self.logger = logging.getLogger(name)
