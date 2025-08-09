from typing import Optional, Any, Literal

from jiter import from_json


class JsonStreamParser:
    """JSON流式解析器 - 纯工具类"""

    def __init__(self, partial_mode: Literal[True, False, "off", "on", "trailing-strings"] = "trailing-strings"):
        """
        初始化解析器

        Args:
            partial_mode: 解析模式
        """
        self.partial_mode = partial_mode

    def parse(self, content: str) -> Optional[Any]:
        """
        解析JSON内容

        Args:
            content: 完整的内容字符串

        Returns:
            解析结果，如果解析失败则返回None
        """
        if not content:
            return None

        content = content.strip()
        try:
            # 使用jiter的部分模式解析JSON
            return from_json(
                bytes(content, "utf-8"),
                partial_mode=self.partial_mode
            )
        except Exception:
            # 解析失败时返回None
            return None
