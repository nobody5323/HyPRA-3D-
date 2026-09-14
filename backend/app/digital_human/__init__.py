"""digital_human 子包：数字人驱动（后端产出驱动数据，前端负责渲染）。

- models.py          time axis 数据模型（viseme / face / body）
- viseme.py          文本或字级时间戳 → 口型时间轴
- base.py            DigitalHumanProvider 接口
- local_provider.py  本地降级实现（零依赖）
- xmov_provider.py   魔珐星云实现（TTS WebSocket：音频 + 字级时间戳）

设计参照：魔珐星云「四路参数流」（audio / body / face / event）思想，
后端只产出参数与时间轴，渲染交由前端 SDK。
"""
