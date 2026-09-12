"""LangGraph 编排：把一轮对话串成可测试、可视化的节点图。

     START
       ↓
   load_persona          渲染人设（状态变量替换）
       ↓
   worldbook_recall      关键词/正则触发 + 注入编排
       ↓
   memory_recall         温层语义召回 + 冷层事实 + 摘要
       ↓
   assemble_prompt       PromptManager 分层组装（固定顺序 + 预算）
       ↓
   generate_reply        LLM 生成回复
       ↓
   write_memory          事件驱动写入（事实/向量/摘要）
       ↓
      END

设计取舍：
- 图为**无状态纯编排**：会话读写由 chat 路由负责，节点只做计算与记忆写入；
- 依赖（人设/世界书/记忆/LLM）经 ChatNodes 注入，便于测试与替换；
- 节点粒度对齐设计参照①的装配顺序，M4 情绪节点可直接插在 generate 前后。
"""

from langgraph.graph import END, START, StateGraph

from app.graph.nodes import ChatNodes
from app.graph.state import ChatState

# 节点名（与 ChatNodes 方法一一对应）
NODE_LOAD_PERSONA = "load_persona"
NODE_WORLDBOOK = "worldbook_recall"
NODE_MEMORY = "memory_recall"
NODE_ASSEMBLE = "assemble_prompt"
NODE_GENERATE = "generate_reply"
NODE_WRITE_MEMORY = "write_memory"

# 节点执行顺序
NODE_SEQUENCE = [
    NODE_LOAD_PERSONA,
    NODE_WORLDBOOK,
    NODE_MEMORY,
    NODE_ASSEMBLE,
    NODE_GENERATE,
    NODE_WRITE_MEMORY,
]


def build_chat_graph(nodes: ChatNodes):
    """编译对话编排图（返回可直接 invoke 的 CompiledStateGraph）。"""
    builder = StateGraph(ChatState)

    builder.add_node(NODE_LOAD_PERSONA, nodes.load_persona)
    builder.add_node(NODE_WORLDBOOK, nodes.worldbook_recall)
    builder.add_node(NODE_MEMORY, nodes.memory_recall)
    builder.add_node(NODE_ASSEMBLE, nodes.assemble_prompt)
    builder.add_node(NODE_GENERATE, nodes.generate_reply)
    builder.add_node(NODE_WRITE_MEMORY, nodes.write_memory)

    builder.add_edge(START, NODE_LOAD_PERSONA)
    for current, nxt in zip(NODE_SEQUENCE, NODE_SEQUENCE[1:]):
        builder.add_edge(current, nxt)
    builder.add_edge(NODE_WRITE_MEMORY, END)

    return builder.compile()
