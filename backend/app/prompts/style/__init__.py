"""style 子包：文风预设（人设之外的第二维度）。

- models.py    StylePreset / StyleExample 数据模型
- loader.py    YAML 加载 + 「风格 × 人设」一致性校验
- presets/     自创风格预设（现代口语 / 古典雅致 / 简短利落 / 细腻长句）

设计参照 SillyTavern 的 Author's Note 深度注入与 example messages 机制
（仅借鉴机制思想，预设文本全部自创）。
"""
