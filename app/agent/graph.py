"""
LangGraph 图定义
将节点连接成有向图，定义状态流转
"""
from typing import AsyncGenerator, Dict, Any

from app.agent.nodes import analyze_node, retrieve_node, generate_node, deduplicate_citations


def should_retrieve(state: Dict[str, Any]) -> str:
    """条件边：判断是否需要检索"""
    intent = state.get("intent", "need_rag")
    if intent == "need_rag":
        return "retrieve"
    return "generate"


async def run_agent(query: str, session_id: str) -> Dict[str, Any]:
    """
    运行智能体（同步返回完整结果）

    流程：analyze → [retrieve] → generate
    """
    # 初始化状态
    state: Dict[str, Any] = {
        "query": query,
        "session_id": session_id,
        "intent": None,
        "rewritten_query": None,
        "context_docs": [],
        "answer": "",
        "citations": [],
        "streamed_chunks": [],
        "error": None,
        "current_node": None,
    }

    # 1. 分析节点（意图识别 + 改写，单节点）
    state.update(await analyze_node(state))

    # 2. 条件分支：是否需要检索
    if state["intent"] == "need_rag":
        retrieve_result = await retrieve_node(state)
        state.update(retrieve_result)

    # 3. 生成回答
    state.update(await generate_node(state))

    return state


async def stream_agent(
    query: str,
    session_id: str,
    history_messages: list = None,
) -> AsyncGenerator[dict, None]:
    """
    运行智能体（流式返回）

    流程：analyze → [retrieve] → generate (stream)

    Args:
        query: 用户问题
        session_id: 会话 ID
        history_messages: 历史消息列表

    Yields:
        dict 格式的流式事件：
        - {"type": "analyze", "intent": "...", "reason": "..."} - 分析结果
        - {"type": "chunk", "content": "..."} - 生成的文本块
        - {"type": "citations", "citations": [...]} - 引用来源
        - {"type": "done"} - 完成信号
    """
    from app.services.llm_service import llm_service
    from app.services.qdrant_service import qdrant_service
    from app.core.config import settings
    from app.agent.nodes import RAG_GENERATE_PROMPT, DIRECT_GENERATE_PROMPT

    history_messages = history_messages or []

    # 1. 构建历史上下文字符串（用于 analyze 节点）
    history_text = ""
    if len(history_messages) > 0:
        # 取最近 3 轮作为上下文
        recent = history_messages[-6:] if len(history_messages) > 6 else history_messages
        history_text = "\n".join([
            f"{'用户' if m['role'] == 'user' else '助手'}: {m['content'][:100]}"
            for m in recent
        ])

    # 2. 分析节点（极简规则路由，<1ms）
    # 从 query 中提取真正的用户问题（去掉引用部分 ">" 开头的行）
    import re
    lines = query.split('\n')
    real_query = '\n'.join(line for line in lines if not line.strip().startswith('>')).strip()

    analyze_result = await analyze_node({
        "query": real_query,
        "history": history_text,
    })

    intent = analyze_result.get("intent", "need_rag")
    rewritten_query = analyze_result.get("rewritten_query", real_query)

    # 3. 条件分支：是否需要检索
    context_docs = []
    if intent == "need_rag":
        try:
            # 召回更多片段（top_k=10），后续按父文档去重
            context_docs = await qdrant_service.asearch(rewritten_query, top_k=10)
        except Exception:
            context_docs = []

    # 4. 构建生成 prompt（使用完整 query，包含引用部分）
    # 5. 构建消息历史（暂时禁用，方便后续加回）
    context = "\n\n".join([doc["content"] for doc in context_docs[:5]])

    if intent == "need_rag" and context_docs:
        system_prompt = RAG_GENERATE_PROMPT.format(
            context=context,
            query=query,
        )
    else:
        system_prompt = DIRECT_GENERATE_PROMPT.format(query=query)

    # 5. 构建消息历史（暂时禁用，方便后续加回）
    # TODO: 后续可以在这里加回上下文
    # if history_messages:
    #     messages.extend(history_messages)
    messages = [{"role": "user", "content": query}]

    # 6. 流式生成（使用强力模型）
    async for chunk in llm_service.stream_chat(
        messages,
        system_prompt,
        model=settings.quality_model,
    ):
        if chunk.startswith("data: ") and chunk != "data: [DONE]\n\n":
            content = chunk[6:]
            yield {"type": "chunk", "content": content}

    # 7. 输出引用信息（按父文档去重）
    if context_docs:
        unique_docs = deduplicate_citations(context_docs)
        citations = [
            {
                "source": doc.get("metadata", {}).get("source", ""),
                "doc_title": doc.get("metadata", {}).get("doc_title", ""),
                "score": doc.get("score", 0),
            }
            for doc in unique_docs[:5]
        ]
        yield {"type": "citations", "citations": citations}

    # 8. 完成信号
    yield {"type": "done"}
