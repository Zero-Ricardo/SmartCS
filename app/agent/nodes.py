"""
LangGraph 节点函数
"""
from typing import Dict, Any
from app.core.config import settings
from app.services.llm_service import llm_service


# RAG 场景的生成提示词（严格基于参考资料）
RAG_GENERATE_PROMPT = """你是上海淘课公司的智能客服助手,同时你是上海淘课公司的客服前台,请严格根据以下参考资料回答用户和访客的问题。

【参考资料】
{context}

【回答要求】
1. 【仅基于】参考资料内容作答，做到精简、准确
2. 如果资料中没有答案，明确说明"根据现有资料，暂未找到相关信息"
3. 不要编造资料中没有的信息
4. 保持专业、友好的语气
5. 直接给出回答，不要提及"参考资料"等元信息
6. 只能回答关于本公司的业务相关的咨询问题,遇到用户问不相关的问题就回答:"抱歉,我只能回复与业务相关的咨询问题"

【用户问题】
{query}

【参考问答对】
用户问的问题可能清晰也可能模糊,但是你要明白用户最终想要得到什么答案,下面是两个样例回答,你后续回答的时候只需要回答出"ground_truth"字段后面的内容.
 "question_clear": "在培训宝项目中如何新建面授学习任务？", 
 "question_vague": "线下培训咋建？", 
 "ground_truth": "打开一个培训项目后，点击左侧的“更多”菜单；出现更多菜单面板后，点击面授学习。"

"question_clear": "学员完成面授学习的判定标准是什么？", 
"question_vague": "员工怎么才算学完线下课？", 
"ground_truth": "学员签到了该面授学习关联的签到，则代表学员参加完成了这个面授学习。注意：面授学习是否完成，只跟面授学习所关联的签到有关。"

请直接回答：
"""

# 直接回答场景的生成提示词（无参考资料）
DIRECT_GENERATE_PROMPT = """你是上海淘课公司的客服前台,你提供友好、专业的公司前台服务。请简洁清晰地回答用户的问题。
只能回答关于本公司的业务相关的咨询问题,遇到用户问不相关的问题就回答:"抱歉,我只能回复与业务相关的咨询问题".
如果用户的问题是咨询问题,就正常回答,遇到不确定的问题就说不知道,不会误导别人

【用户问题】
{query}

请直接回答：
"""


async def analyze_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    意图分析节点：使用本地极简规则路由，将 18 秒延迟降为 1 毫秒
    """
    query = state.get("query", "").strip()

    # 定义常见的闲聊触发词
    chat_keywords = ["你好", "在吗", "你是谁", "怎么称呼", "hi", "hello", "早上好", "下午好", "笨", "傻"]

    # 规则判断：如果句子很短，且包含闲聊词汇，直接判定为闲聊
    if len(query) < 15 and any(kw in query.lower() for kw in chat_keywords):
        return {
            "intent": "direct_answer",
            "original_query": query,
            "rewritten_query": query  # 不改写
        }

    # 其他所有情况（业务问题），一律放行去走 RAG 检索
    return {
        "intent": "need_rag",
        "original_query": query,
        "rewritten_query": query  # 暂时不引入大模型改写，追求极致速度
    }


async def retrieve_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    向量检索节点（异步）
    """
    from app.services.qdrant_service import qdrant_service

    query = state.get("rewritten_query", state.get("query", ""))
    top_k = state.get("top_k", 3)

    try:
        docs = await qdrant_service.asearch(query, top_k=top_k)
        return {
            "context_docs": docs,
            "current_node": "retrieve",
        }
    except Exception as e:
        return {
            "context_docs": [],
            "error": str(e),
            "current_node": "retrieve",
        }


async def generate_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LLM 生成节点（流式）

    根据上下文生成回答，使用强力模型
    """
    query = state.get("query", "")
    context_docs = state.get("context_docs", [])
    intent = state.get("intent", "direct_answer")

    # 构建上下文
    context = "\n\n".join([doc["content"] for doc in context_docs])

    # 构建 system prompt
    if intent == "need_rag" and context_docs:
        system_prompt = RAG_GENERATE_PROMPT.format(
            context=context,
            query=query,
        )
    else:
        system_prompt = DIRECT_GENERATE_PROMPT.format(query=query)

    messages = [{"role": "user", "content": query}]

    # 流式生成（使用强力模型）
    full_response = ""
    streamed_chunks = []

    async for chunk in llm_service.stream_chat(
        messages,
        system_prompt,
        model=settings.quality_model,
    ):
        if chunk.startswith("data: ") and chunk != "data: [DONE]\n\n":
            content = chunk[6:]
            full_response += content
            streamed_chunks.append(chunk)

    # 构建引用
    citations = [
        {"content": doc["content"], "score": doc["score"]}
        for doc in context_docs
    ]

    return {
        "answer": full_response,
        "citations": citations,
        "streamed_chunks": streamed_chunks,
        "current_node": "generate",
    }
