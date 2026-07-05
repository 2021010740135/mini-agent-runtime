"""文档读取工具——读取项目内的文件内容"""

import os

from .base import BaseTool


class ReadDocsTool(BaseTool):
    """读取指定文件的内容。

    出于安全考虑，仅允许读取 base_dir 目录下的文件。
    """

    name = "read_docs"
    description = "读取项目内的文档或代码文件内容"

    parameters = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "要读取的文件路径（相对于项目根目录），如 'README.md' 或 'src/main.py'",
            },
        },
        "required": ["file_path"],
    }

    # 默认读取的根目录，可通过构造函数覆盖
    def __init__(self, base_dir: str | None = None) -> None:
        super().__init__()
        self.base_dir = base_dir or os.getcwd()

    async def execute(self, **kwargs) -> str:
        """读取文件内容并返回。

        Args:
            file_path: 文件路径（相对于 base_dir）

        Returns:
            文件内容字符串（含行号），或错误信息
        """
        file_path = kwargs.get("file_path", "").strip()
        if not file_path:
            return "错误：file_path 不能为空"

        # 安全检查：防止路径穿越
        full_path = os.path.normpath(os.path.join(self.base_dir, file_path))
        if not full_path.startswith(os.path.normpath(self.base_dir)):
            return f"错误：不允许访问 base_dir 以外的路径 '{file_path}'"

        if not os.path.isfile(full_path):
            return f"错误：文件不存在 '{file_path}'"

        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            return f"错误：文件 '{file_path}' 不是文本文件"
        except Exception as e:
            return f"错误：读取文件失败 '{file_path}' - {e}"

        if not content:
            return f"文件 '{file_path}' 内容为空"

        # 带上行号返回
        lines = content.split("\n")
        numbered = [
            f"{i+1:>4}  {line}"
            for i, line in enumerate(lines)
        ]
        return "\n".join(numbered)