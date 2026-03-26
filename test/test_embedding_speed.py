"""测试 embedding 速度"""
import sys
sys.path.insert(0, "X:\\智能体开发\\SmartCS")

import time
import asyncio
from app.services.qdrant_service import qdrant_service


async def test_embedding_speed():
    query = "培训宝如何支持线下培训的互动和考试"

    print(f"Testing query: {query}")
    print("=" * 50)

    # Test async embedding
    start = time.time()
    embedding = await qdrant_service.aget_dense_embedding(query)
    elapsed = time.time() - start

    print(f"Embedding time: {elapsed:.3f}s")
    print(f"Vector dim: {len(embedding)}")


if __name__ == "__main__":
    asyncio.run(test_embedding_speed())
