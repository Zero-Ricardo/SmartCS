#!/usr/bin/env python3
"""测试 SSE 流式输出的时间分布"""
import requests
import time
import sys

def test_stream_timing():
    url = "http://localhost:8000/internal/chat/stream"
    headers = {
        "Content-Type": "application/json",
        "X-Internal-Secret": "your-internal-secret-key",
    }
    data = {
        "query": "培训宝如何支持线下培训的互动和考试",
        "guest_id": "test_timing",
    }

    print("开始测试 SSE 流式输出时间分布...")
    print("=" * 60)

    start_time = time.time()
    first_byte_time = None
    chunk_count = 0
    chunk_times = []

    response = requests.post(url, json=data, headers=headers, stream=True)

    for line in response.iter_lines():
        if line:
            now = time.time()
            elapsed = now - start_time

            if first_byte_time is None:
                first_byte_time = elapsed
                print(f"首字节时间 (TTFB): {elapsed:.3f}s")

            decoded = line.decode('utf-8')
            if decoded.startswith('data: '):
                content = decoded[6:]
                chunk_count += 1
                chunk_times.append((elapsed, len(content), content[:30]))

    total_time = time.time() - start_time

    print(f"总耗时: {total_time:.3f}s")
    print(f"总共收到 {chunk_count} 个 chunk")
    print(f"平均每 chunk 间隔: {(total_time - first_byte_time) / max(chunk_count-1, 1):.3f}s" if chunk_count > 1 else "")

    # 显示前10个和后5个chunk的时间分布
    print("\n前 10 个 chunk 时间分布:")
    for i, (t, length, content) in enumerate(chunk_times[:10]):
        print(f"  [{i+1:2d}] t={t:.3f}s, len={length:3d}, content={content!r}")

    if len(chunk_times) > 15:
        print("\n... (省略中间 chunk) ...\n")
        print("后 5 个 chunk 时间分布:")
        for i, (t, length, content) in enumerate(chunk_times[-5:]):
            print(f"  [{len(chunk_times)-5+i+1:2d}] t={t:.3f}s, len={length:3d}, content={content!r}")

if __name__ == "__main__":
    test_stream_timing()
