"""FastAPI 路由层。

- chat.py      POST /chat（提示组装骨架，LLM 待接入）
- （后续新增 memory / media 路由子模块，在此统一导出）
"""

from app.api.chat import router as chat_router

__all__ = ["chat_router"]
