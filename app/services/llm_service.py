from typing import AsyncGenerator, Optional
from openai import AsyncOpenAI
from app.core.config import settings


class LLMService:
    """LLM 服务：流式输出"""

    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_api_base,
        )
        self.model = settings.openai_model

    async def stream_chat(
        self,
        messages: list,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """流式聊天"""
        # 构建消息
        chat_messages = []
        if system_prompt:
            chat_messages.append({"role": "system", "content": system_prompt})
        chat_messages.extend(messages)

        # 调用 OpenAI API
        response = await self.client.chat.completions.create(
            model=model or self.model,
            messages=chat_messages,
            stream=True,
            temperature=0.7,
        )

        # 流式输出
        async for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                yield f"data: {content}\n\n"

        yield "data: [DONE]\n\n"

    async def quick_chat(
        self,
        messages: list,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
    ) -> str:
        """
        非流式快速对话（用于意图识别等简单任务）
        返回完整文本，不流式输出
        """
        chat_messages = []
        if system_prompt:
            chat_messages.append({"role": "system", "content": system_prompt})
        chat_messages.extend(messages)

        response = await self.client.chat.completions.create(
            model=model or self.model,
            messages=chat_messages,
            stream=False,
            temperature=0.3,  # 低温度，更确定
        )

        return response.choices[0].message.content


# 全局服务实例
llm_service = LLMService()
