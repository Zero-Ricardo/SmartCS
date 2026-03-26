"""
测试反馈接口
"""
import asyncio
import httpx
import os
import sys

# 修复 Windows 控制台编码问题
sys.stdout.reconfigure(encoding='utf-8')

# 添加项目根目录到 path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings

BASE_URL = "http://localhost:8000"
INTERNAL_SECRET = settings.internal_secret


async def test_feedback():
    """测试反馈接口"""

    async with httpx.AsyncClient(timeout=30.0) as client:

        # 1. 先创建一个会话并发送消息，获取 assistant 消息 ID
        print("=" * 50)
        print("Step 1: 创建会话并发送消息...")
        print("=" * 50)

        chat_payload = {
            "guest_id": "test_guest_feedback",
            "query": "什么是 SmartCS？"
        }

        headers = {
            "X-Internal-Secret": INTERNAL_SECRET,
            "Content-Type": "application/json"
        }

        # 发送聊天请求，获取 SSE 流
        async with client.stream(
            "POST",
            f"{BASE_URL}/internal/chat/stream",
            json=chat_payload,
            headers=headers,
        ) as response:
            print(f"状态码: {response.status_code}")

            session_id = None
            full_response = ""

            async for line in response.aiter_lines():
                if line.startswith("event: session"):
                    # 下一行是 data
                    continue
                elif line.startswith("data:"):
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    elif data.startswith("{") and "session_id" in data:
                        import json
                        session_id = json.loads(data)["session_id"]
                        print(f"会话 ID: {session_id}")
                    else:
                        full_response += data

            print(f"AI 回复长度: {len(full_response)} 字符")
            print(f"AI 回复预览: {full_response[:100]}...")

        if not session_id:
            print("❌ 无法获取 session_id")
            return

        # 2. 获取该会话的消息列表，找到 assistant 消息
        print("\n" + "=" * 50)
        print("Step 2: 获取消息列表...")
        print("=" * 50)

        messages_response = await client.get(
            f"{BASE_URL}/internal/chat/messages",
            params={"session_id": session_id},
            headers=headers,
        )

        print(f"状态码: {messages_response.status_code}")
        messages = messages_response.json()

        assistant_msg = None
        for msg in messages:
            print(f"  - [{msg['role']}] {msg['id'][:8]}...")
            if msg["role"] == "assistant":
                assistant_msg = msg

        if not assistant_msg:
            print("❌ 没有找到 assistant 消息")
            return

        message_id = assistant_msg["id"]
        print(f"\n找到 assistant 消息: {message_id}")

        # 3. 测试反馈接口 - 点赞 (up)
        print("\n" + "=" * 50)
        print("Step 3: 测试点赞反馈 (up)...")
        print("=" * 50)

        feedback_payload = {
            "message_id": message_id,
            "feedback": "up"
        }

        feedback_response = await client.post(
            f"{BASE_URL}/internal/chat/feedback",
            json=feedback_payload,
            headers=headers,
        )

        print(f"状态码: {feedback_response.status_code}")
        result = feedback_response.json()
        print(f"响应: {result}")

        if result.get("success"):
            print("✅ 点赞成功！")
        else:
            print(f"❌ 点赞失败: {result.get('message')}")

        # 4. 测试反馈接口 - 点踩 (down)
        print("\n" + "=" * 50)
        print("Step 4: 测试点踩反馈 (down)...")
        print("=" * 50)

        feedback_payload["feedback"] = "down"

        feedback_response = await client.post(
            f"{BASE_URL}/internal/chat/feedback",
            json=feedback_payload,
            headers=headers,
        )

        print(f"状态码: {feedback_response.status_code}")
        result = feedback_response.json()
        print(f"响应: {result}")

        if result.get("success"):
            print("✅ 点踩成功！")
        else:
            print(f"❌ 点踩失败: {result.get('message')}")

        # 5. 测试无效反馈类型
        print("\n" + "=" * 50)
        print("Step 5: 测试无效反馈类型...")
        print("=" * 50)

        feedback_payload["feedback"] = "invalid"

        feedback_response = await client.post(
            f"{BASE_URL}/internal/chat/feedback",
            json=feedback_payload,
            headers=headers,
        )

        print(f"状态码: {feedback_response.status_code}")
        result = feedback_response.json()
        print(f"响应: {result}")

        if not result.get("success"):
            print("✅ 正确拒绝了无效反馈类型！")
        else:
            print("❌ 应该拒绝无效反馈类型")

        # 6. 测试不存在的消息
        print("\n" + "=" * 50)
        print("Step 6: 测试不存在的消息...")
        print("=" * 50)

        feedback_payload["message_id"] = "00000000-0000-0000-0000-000000000000"
        feedback_payload["feedback"] = "up"

        feedback_response = await client.post(
            f"{BASE_URL}/internal/chat/feedback",
            json=feedback_payload,
            headers=headers,
        )

        print(f"状态码: {feedback_response.status_code}")
        result = feedback_response.json()
        print(f"响应: {result}")

        if not result.get("success") and "不存在" in result.get("message", ""):
            print("✅ 正确处理了不存在的消息！")
        else:
            print("❌ 应该返回消息不存在")

        print("\n" + "=" * 50)
        print("测试完成！")
        print("=" * 50)


if __name__ == "__main__":
    asyncio.run(test_feedback())
