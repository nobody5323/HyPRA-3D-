"""llm 子包：LLM 对话生成抽象与实现。

- base.py     接口与消息模型
- mock.py     无 key 占位实现（默认）
- factory.py  按配置创建 provider

真实云端实现（dashscope / siliconflow / openai-compatible）接入后
置于本包，并在 factory 注册。
"""
