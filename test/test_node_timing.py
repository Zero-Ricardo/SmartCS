"""测试各节点耗时"""
import sys
sys.path.insert(0, "X:/智能体开发/SmartCS")

import time
import asyncio
from app.agent.nodes import analyze_node


async def test_timing():
    query = "培训宝如何支持线下培训的互动和考试"

    print(f"Testing: {query}")
    print("=" * 50)

    # Test analyze_node
    start = time.time()
    result = await analyze_node({"query": query, "history": ""})
    elapsed = time.time() - start

    print(f"analyze_node: {elapsed:.3f}s")
    print(f"  intent: {result.get('intent')}")
    print(f"  rewritten: {result.get('rewritten_query')}")
    print(f"  reason: {result.get('reason', '')[:50]}...")


if __name__ == "__main__":
    asyncio.run(test_timing())
