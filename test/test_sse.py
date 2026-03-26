"""
SSE 流式输出测试脚本
"""
import requests
import os

# 禁用代理
os.environ["HTTP_PROXY"] = ""
os.environ["HTTPS_PROXY"] = ""
os.environ["http_proxy"] = ""
os.environ["https_proxy"] = ""

BASE_URL = "http://127.0.0.1:8000"
INTERNAL_SECRET = "your-internal-secret-key"

HEADERS = {
    "X-Internal-Secret": INTERNAL_SECRET,
    "Content-Type": "application/json",
}

# 设置 session 不使用代理
session = requests.Session()
session.trust_env = False


def test_stream():
    """测试 SSE 流式输出"""
    print("=" * 50)
    print("SSE 流式聊天测试")
    print("=" * 50)

    response = session.post(
        f"{BASE_URL}/internal/chat/stream",
        headers=HEADERS,
        json={
            "guest_id": "test-guest-stream",
            "query": "你好，请介绍一下自己",
        },
        stream=True,
    )

    print(f"\n状态码: {response.status_code}")
    print(f"Content-Type: {response.headers.get('Content-Type')}")

    if response.status_code != 200:
        print(f"\n错误响应: {response.text}")
        return

    print("\n流式输出:")
    print("-" * 30)

    char_count = 0
    for line in response.iter_lines():
        if line:
            line = line.decode("utf-8")
            if line.startswith("data: "):
                data = line[6:]  # 去掉 "data: " 前缀
                if data == "[DONE]":
                    print("\n" + "-" * 30)
                    print(f"流式输出完成，总计 {char_count} 个字符")
                    break
                print(data, end="", flush=True)
                char_count += 1


if __name__ == "__main__":
    test_stream()
