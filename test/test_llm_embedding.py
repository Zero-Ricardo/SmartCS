"""
测试 LLM 和 Embedding 模型连接
"""
import os
import sys

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 禁用代理
os.environ["HTTP_PROXY"] = ""
os.environ["HTTPS_PROXY"] = ""
os.environ["NO_PROXY"] = "localhost,127.0.0.1"

import requests
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

# 直接从环境变量读取配置
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
EMBEDDING_API_BASE = os.getenv("EMBEDDING_API_BASE", "https://api.openai.com/v1")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

session = requests.Session()
session.trust_env = False


def test_llm():
    """测试 LLM 模型"""
    print("=" * 50)
    print("测试 LLM 模型")
    print("=" * 50)
    print(f"API Base: {OPENAI_API_BASE}")
    print(f"Model: {OPENAI_MODEL}")
    print(f"API Key: {OPENAI_API_KEY[:10]}..." if OPENAI_API_KEY else "API Key: None")
    print()

    url = f"{OPENAI_API_BASE}/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    data = {
        "model": OPENAI_MODEL,
        "messages": [{"role": "user", "content": "你好，请说一句话"}],
        "max_tokens": 50,
    }

    try:
        resp = session.post(url, headers=headers, json=data, timeout=60)
        print(f"状态码: {resp.status_code}")

        if resp.status_code == 200:
            result = resp.json()
            content = result["choices"][0]["message"]["content"]
            print(f"✅ LLM 成功: {content}")
        else:
            print(f"❌ LLM 失败: {resp.text}")
    except Exception as e:
        print(f"❌ LLM 异常: {e}")


def test_embedding():
    """测试 Embedding 模型"""
    print("\n" + "=" * 50)
    print("测试 Embedding 模型")
    print("=" * 50)
    print(f"API Base: {EMBEDDING_API_BASE}")
    print(f"Model: {EMBEDDING_MODEL}")
    print(f"API Key: {OPENAI_API_KEY[:10]}..." if OPENAI_API_KEY else "API Key: None")
    print()

    url = f"{EMBEDDING_API_BASE}/embeddings"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    data = {
        "model": EMBEDDING_MODEL,
        "input": "测试文本",
    }

    try:
        resp = session.post(url, headers=headers, json=data, timeout=30)
        print(f"状态码: {resp.status_code}")

        if resp.status_code == 200:
            result = resp.json()
            embedding = result["data"][0]["embedding"]
            print(f"✅ Embedding 成功: 向量维度 = {len(embedding)}")
        else:
            print(f"❌ Embedding 失败: {resp.text}")
    except Exception as e:
        print(f"❌ Embedding 异常: {e}")


if __name__ == "__main__":
    test_llm()
    test_embedding()
