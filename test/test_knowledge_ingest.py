# -*- coding: utf-8 -*-
"""
测试知识库导入流程：语义切分 + 向量化入库
"""
import sys
import os
import re

import os
print(f"HTTP_PROXY={os.environ.get('HTTP_PROXY', 'NOT SET')}")
print(f"HTTPS_PROXY={os.environ.get('HTTPS_PROXY', 'NOT SET')}")

# Windows 控制台编码
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.text_splitter import text_splitter
from app.services.qdrant_service import qdrant_service


def read_reference_doc(filename: str) -> str:
    """读取参考文档"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    filepath = os.path.join(base_dir, "参考文档", filename)
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def extract_source(text: str) -> str:
    """从文档中提取原文链接"""
    match = re.search(r"# 原文链接: (https?://[^\s]+)", text)
    return match.group(1) if match else ""


def test_semantic_split():
    """测试语义切分"""
    print("=" * 60)
    print("[Step 1] 测试语义切分")
    print("=" * 60)

    text = read_reference_doc("001_金龙鱼：如何玩转培训神器-培训宝.md")
    source = extract_source(text)

    documents = text_splitter.split_text(
        text=text,
        source=source,
        doc_title="001_金龙鱼.md",
    )

    print(f"\n切分结果: {len(documents)} 个文档块\n")

    for i, doc in enumerate(documents[:5], 1):  # 只显示前 5 个
        print(f"--- 块 {i} ---")
        print(f"类型: {doc.metadata.get('type')}")
        print(f"层级: H2={doc.metadata.get('H2')} | H3={doc.metadata.get('H3')} | H4={doc.metadata.get('H4')}")
        print(f"长度: {len(doc.page_content)} 字符")
        print(f"内容: {doc.page_content[:100]}...")
        print()

    return documents


def test_qdrant_operations():
    """测试 Qdrant 操作"""
    print("=" * 60)
    print("[Step 2] 测试 Qdrant 操作")
    print("=" * 60)

    # 删除旧集合（如果存在）
    collection_name = "test_knowledge"
    if qdrant_service.collection_exists(collection_name):
        print(f"删除旧集合: {collection_name}")
        qdrant_service.delete_collection(collection_name)

    # 切分文档
    text = read_reference_doc("001_金龙鱼：如何玩转培训神器-培训宝.md")
    source = extract_source(text)

    documents = text_splitter.split_text(
        text=text,
        source=source,
        doc_title="001_金龙鱼.md",
    )

    # 入库
    print(f"\n入库 {len(documents)} 个文档块到集合: {collection_name}")
    ids = qdrant_service.add_documents(documents, collection_name)
    print(f"成功入库 {len(ids)} 个向量")

    # 检查索引
    print("\n检查 payload 索引...")
    try:
        collection_info = qdrant_service.qdrant_client.get_collection(collection_name)
        print(f"集合向量数: {collection_info.points_count}")
    except Exception as e:
        print(f"获取集合信息失败: {e}")

    return collection_name


def test_search(collection_name: str):
    """测试向量检索"""
    print("=" * 60)
    print("[Step 3] 测试向量检索")
    print("=" * 60)

    queries = [
        "金龙鱼是什么公司？",
        "培训宝有什么功能？",
    ]

    for query in queries:
        print(f"\n查询: {query}")
        print("-" * 40)

        results = qdrant_service.search(
            query=query,
            collection_name=collection_name,
            top_k=3,
        )

        for i, result in enumerate(results, 1):
            metadata = result.get("metadata", {})
            print(f"  [{i}] 分数: {result['score']:.4f}")
            print(f"      来源: {metadata.get('source', 'N/A')}")
            print(f"      章节: {metadata.get('H2')} -> {metadata.get('H3')}")
            print(f"      内容: {result['content'][:80]}...")
            print()


def test_filter_search(collection_name: str):
    """测试带过滤条件的检索"""
    print("=" * 60)
    print("[Step 4] 测试带过滤条件的检索")
    print("=" * 60)

    query = "培训"
    print(f"\n查询: {query}")
    print("过滤条件: type=normal")
    print("-" * 40)

    results = qdrant_service.search(
        query=query,
        collection_name=collection_name,
        top_k=3,
        filter_conditions={"type": "normal"},
    )

    for i, result in enumerate(results, 1):
        metadata = result.get("metadata", {})
        print(f"  [{i}] 分数: {result['score']:.4f}")
        print(f"      类型: {metadata.get('type')}")
        print(f"      内容: {result['content'][:80]}...")
        print()


if __name__ == "__main__":
    print("\n[START] 开始测试知识库导入流程\n")

    # Step 1: 测试切分
    docs = test_semantic_split()

    # Step 2: 测试 Qdrant 操作
    collection_name = test_qdrant_operations()

    # Step 3: 测试检索
    test_search(collection_name)

    # Step 4: 测试过滤检索
    test_filter_search(collection_name)

    # 清理测试集合
    print("=" * 60)
    print("[CLEANUP] 清理测试集合")
    print("=" * 60)
    qdrant_service.delete_collection(collection_name)
    print(f"已删除集合: {collection_name}")

    print("\n[DONE] 测试完成!")
