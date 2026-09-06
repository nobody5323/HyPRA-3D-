"""世界书条目数据模型（借鉴 SillyTavern World Info 机制思想，自写实现）。

一个条目 = 触发条件（关键词 + 可选正则）+ 注入内容 + 控制参数。
"""

from pydantic import BaseModel, Field


class WorldBookEntry(BaseModel):
    """世界书条目。

    keys      关键词列表：对话文本中出现任一关键词（默认不区分大小写）即触发；
    regex     可选正则模式列表：任一模式 search 命中即触发（与关键词互为补充）；
    content   触发后注入 prompt 的正文；
    enabled   是否参与触发匹配（可整体停用某条目）；
    case_sensitive  关键词是否区分大小写（默认 False = 不区分）；
    priority  注入排序权重（越大越靠前；本批仅预留，注入编排见 M3 PromptManager）。
    """

    id: str = Field(description="条目唯一标识（英文小写连字符）")
    title: str = Field(description="条目标题")
    content: str = Field(description="触发后注入的正文")
    keys: list[str] = Field(default_factory=list, description="关键词列表")
    regex: list[str] = Field(default_factory=list, description="正则触发模式列表")
    enabled: bool = Field(default=True, description="是否参与触发")
    case_sensitive: bool = Field(default=False, description="关键词匹配是否区分大小写")
    priority: int = Field(default=0, description="注入优先级（越大越靠前）")

    @property
    def has_trigger(self) -> bool:
        """是否存在任一触发条件（关键词或正则）。"""
        return bool(self.keys or self.regex)
