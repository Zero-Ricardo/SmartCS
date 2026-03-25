# -*- coding: utf-8 -*-
"""
RAG 检索评估脚本

功能：
1. 检查 pxb 集合是否存在，不存在则创建并入库 pure_md/ 下的所有文档
2. 读取 golden_dataset.jsonl 测试集
3. 对 question_clear 和 question_vague 分别测试
4. 计算 Hit@K 和 MRR
5. 输出评估报告
"""
import sys
import os

# ============================================================
# 网络配置（必须在所有 import 之前）
# ============================================================
# 1. 解决 HuggingFace 下载超时问题（使用国内镜像）
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

# 2. 解决本地 Qdrant 502 问题（本地地址不走代理）
os.environ["no_proxy"] = "localhost,127.0.0.1,::1"
os.environ["NO_PROXY"] = "localhost,127.0.0.1,::1"
# ============================================================

import json
import re

# Windows 控制台编码
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.text_splitter import MarkdownSemanticSplitter
from app.services.qdrant_service import qdrant_service

# ============================================================
# 配置参数（在这里修改）
# ============================================================
COLLECTION_NAME = "pxb"     # Qdrant 集合名称
TOP_K = 5                          # 检索返回的文档数量
CHUNK_SIZE = 500                   # 切分块大小
CHUNK_OVERLAP = 100                # 切分重叠大小
MAX_FAILED_CASES_SHOW = 10         # 最多显示的失败用例数

# 切分优化
INJECT_TITLE_PREFIX = True         # 是否在 chunk 开头注入标题前缀

# 检索优化
USE_HYBRID = True                  # 是否使用混合检索（Dense + Sparse/BM25）
# ============================================================

PURE_MD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pure_md")
GOLDEN_DATASET_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "golden_dataset.jsonl")


def extract_source(text: str) -> str:
    """从文档中提取原文链接"""
    match = re.search(r"# 原文链接: (https?://[^\s]+)", text)
    return match.group(1) if match else ""


def ingest_documents():
    """切分并入库 pure_md/ 下的所有文档"""
    print("=" * 60)
    print("[Step 1] 切分入库文档")
    print("=" * 60)

    # 获取所有 md 文件
    md_files = [f for f in os.listdir(PURE_MD_DIR) if f.endswith(".md")]
    print(f"\n发现 {len(md_files)} 个 Markdown 文件")

    # 删除旧集合（如果存在）
    if qdrant_service.collection_exists(COLLECTION_NAME):
        print(f"删除旧集合: {COLLECTION_NAME}")
        qdrant_service.delete_collection(COLLECTION_NAME)

    # 创建新集合
    print(f"创建集合: {COLLECTION_NAME}")
    qdrant_service.ensure_collection(COLLECTION_NAME)

    # 切分器
    splitter = MarkdownSemanticSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        inject_title_prefix=INJECT_TITLE_PREFIX,
    )

    total_chunks = 0
    for i, filename in enumerate(md_files, 1):
        filepath = os.path.join(PURE_MD_DIR, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # 提取原文链接
        source = extract_source(content)

        # 切分
        chunks = splitter.split_text(
            text=content,
            source=source,
            doc_title=filename,  # 只存文件名
        )

        if chunks:
            # 入库
            qdrant_service.add_documents(chunks, COLLECTION_NAME)
            total_chunks += len(chunks)
            print(f"  [{i}/{len(md_files)}] {filename} -> {len(chunks)} chunks")

    print(f"\n入库完成: {len(md_files)} 个文档, {total_chunks} 个 chunks")

    # 验证
    collection_info = qdrant_service.qdrant_client.get_collection(COLLECTION_NAME)
    print(f"集合向量数: {collection_info.points_count}")


def load_golden_dataset():
    """加载黄金测试集"""
    test_cases = []
    with open(GOLDEN_DATASET_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                test_cases.append(json.loads(line))
    return test_cases


def extract_filename(source_file: str) -> str:
    """从 source_file 提取文件名"""
    # 处理 ./pure_md\\001_xxx.md 或 pure_md/001_xxx.md 等格式
    filename = os.path.basename(source_file.replace("\\", "/"))
    return filename


def evaluate_retrieval():
    """评估检索效果"""
    print("\n" + "=" * 60)
    print("[Step 2] 加载测试集并评估")
    print("=" * 60)

    # 加载测试集
    test_cases = load_golden_dataset()
    print(f"\n加载测试集: {len(test_cases)} 条用例")

    # 评估结果
    clear_results = {"hits": 0, "mrr_sum": 0.0, "total": 0}
    vague_results = {"hits": 0, "mrr_sum": 0.0, "total": 0}
    failed_cases = []

    print("\n开始评估...")
    for i, case in enumerate(test_cases, 1):
        expected_file = extract_filename(case["source_file"])
        question_clear = case["question_clear"]
        question_vague = case["question_vague"]

        # 测试 question_clear
        results_clear = qdrant_service.search(
            query=question_clear,
            collection_name=COLLECTION_NAME,
            top_k=TOP_K,
            use_hybrid=USE_HYBRID,
        )
        retrieved_files_clear = [r["metadata"].get("doc_title", "") for r in results_clear]

        # 计算 clear 指标
        if expected_file in retrieved_files_clear:
            clear_results["hits"] += 1
            rank = retrieved_files_clear.index(expected_file) + 1
            clear_results["mrr_sum"] += 1.0 / rank
        else:
            failed_cases.append({
                "question": question_clear,
                "type": "clear",
                "expected": expected_file,
                "retrieved": retrieved_files_clear[:3],
            })
        clear_results["total"] += 1

        # 测试 question_vague
        results_vague = qdrant_service.search(
            query=question_vague,
            collection_name=COLLECTION_NAME,
            top_k=TOP_K,
            use_hybrid=USE_HYBRID,
        )
        retrieved_files_vague = [r["metadata"].get("doc_title", "") for r in results_vague]

        # 计算 vague 指标
        if expected_file in retrieved_files_vague:
            vague_results["hits"] += 1
            rank = retrieved_files_vague.index(expected_file) + 1
            vague_results["mrr_sum"] += 1.0 / rank
        else:
            failed_cases.append({
                "question": question_vague,
                "type": "vague",
                "expected": expected_file,
                "retrieved": retrieved_files_vague[:3],
            })
        vague_results["total"] += 1

        # 进度显示
        if i % 20 == 0:
            print(f"  已处理: {i}/{len(test_cases)}")

    return clear_results, vague_results, failed_cases


def print_report(clear_results, vague_results, failed_cases):
    """打印评估报告"""
    print("\n" + "=" * 60)
    print("[评估报告]")
    print("=" * 60)

    total_queries = clear_results["total"] + vague_results["total"]
    print(f"\n测试配置:")
    print(f"  测试用例数: {clear_results['total']}")
    print(f"  每用例问题数: 2 (clear + vague)")
    print(f"  总查询次数: {total_queries}")
    print(f"  Top K: {TOP_K}")
    print(f"  标题前缀注入: {INJECT_TITLE_PREFIX}")
    print(f"  混合检索: {USE_HYBRID} (Dense + Sparse/BM25)")

    # Clear Question 结果
    clear_hit_rate = clear_results["hits"] / clear_results["total"] * 100
    clear_mrr = clear_results["mrr_sum"] / clear_results["total"]
    print(f"\nClear Question 结果:")
    print(f"  Hit@{TOP_K}: {clear_results['hits']}/{clear_results['total']} ({clear_hit_rate:.1f}%)")
    print(f"  MRR: {clear_mrr:.4f}")

    # Vague Question 结果
    vague_hit_rate = vague_results["hits"] / vague_results["total"] * 100
    vague_mrr = vague_results["mrr_sum"] / vague_results["total"]
    print(f"\nVague Question 结果:")
    print(f"  Hit@{TOP_K}: {vague_results['hits']}/{vague_results['total']} ({vague_hit_rate:.1f}%)")
    print(f"  MRR: {vague_mrr:.4f}")

    # 综合结果
    avg_hit_rate = (clear_hit_rate + vague_hit_rate) / 2
    avg_mrr = (clear_mrr + vague_mrr) / 2
    print(f"\n综合结果:")
    print(f"  平均 Hit@{TOP_K}: {avg_hit_rate:.1f}%")
    print(f"  平均 MRR: {avg_mrr:.4f}")

    # 失败用例分析
    if failed_cases:
        print(f"\n失败用例 (共 {len(failed_cases)} 个):")
        print("-" * 60)
        # 只显示前 10 个
        for i, case in enumerate(failed_cases[:10], 1):
            print(f"\n[{i}] 类型: {case['type']}")
            print(f"    问题: {case['question'][:50]}...")
            print(f"    期望: {case['expected']}")
            print(f"    实际: {case['retrieved']}")

        if len(failed_cases) > 10:
            print(f"\n... 还有 {len(failed_cases) - 10} 个失败用例未显示")

    print("\n" + "=" * 60)
    print("[DONE] 评估完成")
    print("=" * 60)


def main():
    print("\n[START] RAG 检索评估")
    print(f"集合名称: {COLLECTION_NAME}")
    print(f"文档目录: {PURE_MD_DIR}")
    print(f"测试集: {GOLDEN_DATASET_PATH}")

    # 检查 pxb 集合是否存在
    if qdrant_service.collection_exists(COLLECTION_NAME):
        print(f"\n集合 '{COLLECTION_NAME}' 已存在，跳过入库")
        # 显示集合信息
        try:
            info = qdrant_service.qdrant_client.get_collection(COLLECTION_NAME)
            print(f"集合向量数: {info.points_count}")
        except Exception as e:
            print(f"获取集合信息失败: {e}")
    else:
        # 入库文档
        ingest_documents()

    # 评估检索
    clear_results, vague_results, failed_cases = evaluate_retrieval()

    # 打印报告
    print_report(clear_results, vague_results, failed_cases)


if __name__ == "__main__":
    main()
