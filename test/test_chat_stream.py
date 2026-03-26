"""
测试新 LangGraph 版本的流式聊天接口
"""
import requests
import json
import sys


def test_chat_stream():
    """测试 SSE 流式聊天"""
    url = "http://127.0.0.1:8000/internal/chat/stream"
    headers = {
        "Content-Type": "application/json",
        "X-Internal-Secret": "your-internal-secret-key",
    }

    results = []

    # 测试 1: 闲聊场景
    results.append("=" * 60)
    results.append("Test 1: Chitchat")
    results.append("=" * 60)

    data = {
        "query": "hello",
        "guest_id": "test_guest_001",
    }

    response = requests.post(url, json=data, headers=headers, stream=True)
    results.append(f"Status: {response.status_code}")
    results.append(f"Content-Type: {response.headers.get('content-type')}")
    results.append("")

    full_text = ""
    for line in response.iter_lines():
        if line:
            decoded = line.decode('utf-8')
            results.append(f"  {decoded}")
            if decoded.startswith("data: ") and decoded != "data: [DONE]":
                full_text += decoded[6:]

    results.append(f"Full response: {full_text}")

    # 测试 2: Knowledge Q&A
    results.append("")
    results.append("=" * 60)
    results.append("Test 2: Knowledge Q&A")
    results.append("=" * 60)

    data = {
        "query": "What is SmartCS",
        "guest_id": "test_guest_002",
    }

    response = requests.post(url, json=data, headers=headers, stream=True)
    results.append(f"Status: {response.status_code}")
    results.append("")

    full_text = ""
    citations = []
    for line in response.iter_lines():
        if line:
            decoded = line.decode('utf-8')
            results.append(f"  {decoded}")
            if decoded.startswith("data: ") and decoded != "data: [DONE]":
                full_text += decoded[6:]

    results.append(f"Full response: {full_text[:200]}...")

    # Save results to file
    with open("test_result.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(results))

    print("Test completed. Results saved to test_result.txt")


if __name__ == "__main__":
    test_chat_stream()
