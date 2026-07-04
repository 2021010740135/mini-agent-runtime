"""Mini Agent Runtime — 入口文件"""

import sys
from agent.runtime import AgentRuntime


def main() -> None:
    """启动 agent runtime 主循环."""
    runtime = AgentRuntime()
    runtime.run()


if __name__ == "__main__":
    main()
    sys.exit(0)
