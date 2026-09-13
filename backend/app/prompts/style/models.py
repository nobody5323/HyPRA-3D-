"""风格预设数据模型。

设计原则：**人设（谁）／文风（怎么说话）／模型适配（这个模型吃哪套）三者正交**。

风格预设只描述「怎么说话」，不描述「是谁」——因此可与任意 persona 组合。
结构对齐 SillyTavern 社区验证过的有效手段（只借鉴机制，内容全部自创）：
- style_prompt  正向风格指令（为主，遵循正向:负向 ≈ 3:1）
- avoid         少量必要禁令（只列最刺眼的 AI 腔，避免长串负面清单）
- examples      示例对话（2-3 组，反 AI 化最有效的手段）
- sampling      建议采样参数（可被模型适配档覆盖）
"""

from pydantic import BaseModel, Field


class StyleExample(BaseModel):
    """一组示例对话（few-shot 示范目标语气）。"""

    user: str = Field(description="用户示例发言")
    assistant: str = Field(description="目标风格的助手回应")


class StylePreset(BaseModel):
    """一份文风预设（对应一个 YAML 文件）。"""

    id: str = Field(description="预设唯一标识（英文小写连字符）")
    name: str = Field(description="中文名称")
    description: str = Field(description="一句话说明这种文风的特征")
    tags: list[str] = Field(default_factory=list, description="风格标签")

    style_prompt: str = Field(description="正向风格指令（放 system 末尾，影响更强）")
    avoid: list[str] = Field(
        default_factory=list, description="需要避免的表达（克制使用，只列最刺眼的 AI 腔）"
    )
    examples: list[StyleExample] = Field(
        default_factory=list, description="示例对话（2-3 组，few-shot）"
    )
    sampling: dict[str, float] = Field(
        default_factory=dict, description="建议采样参数（temperature/max_tokens 等）"
    )
    conflicts_with: list[str] = Field(
        default_factory=list,
        description="与人设冲突的特质关键词（用于一致性告警，不阻断）",
    )

    @property
    def instruction_block(self) -> str:
        """拼成注入 system 末尾的风格指令块。

        末尾附一句「示例与用户无关」的声明：实测发现，若不加此说明，
        模型会把示例对话中的具体内容（如「我妈身体不好」）误当作用户的真实情况。
        """
        lines = [f"【表达风格：{self.name}】", self.style_prompt.strip()]
        if self.avoid:
            lines.append("避免：" + "；".join(self.avoid))
        if self.examples:
            lines.append(
                "（注：后续对话示例仅用于示范语气与句长节奏，"
                "示例中的人物与事件与用户本人无关，不得当作已知事实引用。）"
            )
        return "\n".join(lines)

    @property
    def example_count(self) -> int:
        return len(self.examples)
