"""
测试 RAG 服务：文本切分 -> 向量化 -> 检索 -> 问答
"""
import os
import sys

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 禁用代理
os.environ["HTTP_PROXY"] = ""
os.environ["HTTPS_PROXY"] = ""
os.environ["NO_PROXY"] = "localhost,127.0.0.1"

from app.services.rag_service import rag_service

# 测试用的知识库文档 (Markdown 格式)
TEST_DOCUMENT = """
# SmartCS 产品说明书

## 产品简介

SmartCS 是一个 AI 智能客服系统，专注于为企业提供高效、智能的客户服务解决方案。

## 核心功能

### 1. RAG 知识库问答
SmartCS 使用 RAG (Retrieval-Augmented Generation) 技术，能够从企业知识库中检索相关信息，并结合大语言模型生成准确的回答。

### 2. 多轮对话
支持上下文记忆的多轮对话功能，能够理解用户的连续问题，提供连贯的服务体验。

### 3. 访客数据过户
当访客注册成为正式用户时，系统会自动将其历史聊天记录绑定到新账户，确保数据不丢失。

## 技术架构

SmartCS 采用以下技术栈：

- **后端框架**: FastAPI 0.110.0
- **数据库**: PostgreSQL 16
- **向量数据库**: Qdrant 1.8.0
- **LLM**: 支持 OpenAI 兼容 API (如阿里云 **Embedding**: text-embedding-v3 (1024 维向量)

## 部署要求

### 硬件要求
- CPU: 4 核以上
- 内存: 8GB 以上
- 存储: 50GB 以上 SSD

### 软件要求
- Python 3.12+
- Docker & Docker Compose
- PostgreSQL 16

## API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| /internal/chat/stream | POST | SSE 流式聊天 |
| /internal/chat/sessions | GET | 查询会话列表 |
| /internal/chat/bind | POST | 访客数据过户 |

## 联系方式

- 技术支持邮箱: support@smartcs.ai
- 官方网站: https://smartcs.ai
"""


def test_rag_pipeline():
    """测试完整的 RAG 流程"""
    print("=" * 60)
    print("测试 RAG 服务")
    print("=" * 60)

    # 1. 添加文档到向量库
    print("\n[1] 添加文档到向量库...")
    try:
        ids = rag_service.add_texts(
            texts=[TEST_DOCUMENT],
            metadata=[{"source": "产品说明书", "version": "1.0"}],
        )
        print(f"✅ 成功添加 {len(ids)} 个文本块")
    except Exception as e:
        print(f"❌ 添加文档失败: {e}")
        return

    # 2. 测试相似度检索
    print("\n[2] 测试相似度检索...")

    test_questions = [
        "SmartCS 是什么？",
        "RAG 技术有什么用？",
        "系统有哪些硬件要求？",
        "如何联系技术支持？",
    ]

    for question in test_questions:
        print(f"\n问题: {question}")
        try:
            results = rag_service.similarity_search(question, top_k=2)
            if results:
                for i, r in enumerate(results, 1):
                    print(f"  [{i}] 相似度: {r['score']:.3f}")
                    print(f"      内容: {r['content'][:100]}...")
            else:
                print("  未找到相关内容")
        except Exception as e:
            print(f"  ❌ 检索失败: {e}")

    # 3. 清理测试数据
    print("\n[3] 清理测试数据...")
    try:
        rag_service.delete_collection()
        print("✅ 已删除测试集合")
    except Exception as e:
        print(f"❌ 清理失败: {e}")


if __name__ == "__main__":
    test_rag_pipeline()
