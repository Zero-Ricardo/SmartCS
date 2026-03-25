"""
LangGraph 状态定义
定义智能体在执行过程中的状态结构
"""
from typing import TypedDict, List, Optional, Annotated
from operator import add


class AgentState(TypedDict):
    """
    智能体状态

    状态流转：
    用户问题 → 意图识别 → 问题改写 → 向量检索 → LLM 生成 → 输出
    """
    # 输入
    query: str                           # 用户原始问题
    session_id: str                      # 会话 ID

    # 意图识别
    intent: Optional[str]                # 意图类型: "qa" | "chitchat" | "task"
    intent_confidence: Optional[float]   # 意图识别置信度

    # 问题改写
    rewritten_query: Optional[str]       # 改写后的问题（用于检索）
    need_rewrite: bool                   # 是否需要改写

    # 检索结果
    retrieved_docs: List[dict]           # 检索到的文档列表
    retrieval_scores: List[float]        # 检索相似度分数
    has_relevant_context: bool           # 是否有相关上下文

    # 生成结果
    system_prompt: Optional[str]         # 组装后的系统提示
    answer: str                          # LLM 生成的回答
    citations: List[dict]                # 引用来源

    # 流式输出（用于 SSE）
    streamed_chunks: Annotated[List[str], add]  # 流式输出的文本块

    # 错误处理
    error: Optional[str]                 # 错误信息
    current_node: Optional[str]          # 当前执行的节点
