"""
测试 MarkdownSemanticSplitter 切分效果
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.text_splitter import MarkdownSemanticSplitter


def read_reference_doc(filename: str) -> str:
    """读取参考文档"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    filepath = os.path.join(base_dir, "参考文档", filename)
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def extract_source(text: str) -> str:
    """从文档中提取原文链接"""
    import re
    match = re.search(r"# 原文链接: (https?://[^\s]+)", text)
    return match.group(1) if match else ""


def test_split_jinlongyu():
    """测试金龙鱼文档切分"""
    print("=" * 60)
    print("📄 测试文档: 001_金龙鱼：如何玩转培训神器-培训宝.md")
    print("=" * 60)

    text = read_reference_doc("001_金龙鱼：如何玩转培训神器-培训宝.md")
    source = extract_source(text)

    splitter = MarkdownSemanticSplitter(chunk_size=800, chunk_overlap=100)
    documents = splitter.split_text(text, source=source, doc_title="001_金龙鱼.md")

    print(f"\n📊 切分结果: 共 {len(documents)} 个文档块\n")

    for i, doc in enumerate(documents, 1):
        print(f"--- 块 {i} ---")
        print(f"📌 类型: {doc.metadata.get('type', 'unknown')}")
        print(f"📌 来源: {doc.metadata.get('source', 'N/A')}")
        print(f"📌 标题层级:")
        for level in range(1, 7):
            h = doc.metadata.get(f"H{level}", "")
            if h:
                print(f"   H{level}: {h}")
        print(f"📝 内容预览 ({len(doc.page_content)} 字符):")
        # 只显示前 200 字符
        preview = doc.page_content[:200]
        if len(doc.page_content) > 200:
            preview += "..."
        print(f"   {preview}")
        print()

    return documents


def test_split_email():
    """测试邮件通知文档切分"""
    print("=" * 60)
    print("📄 测试文档: 002_如何使用邮件通知-培训宝.md")
    print("=" * 60)

    text = read_reference_doc("002_如何使用邮件通知-培训宝.md")
    source = extract_source(text)

    splitter = MarkdownSemanticSplitter(chunk_size=800, chunk_overlap=100)
    documents = splitter.split_text(text, source=source, doc_title="002_邮件通知.md")

    print(f"\n📊 切分结果: 共 {len(documents)} 个文档块\n")

    for i, doc in enumerate(documents, 1):
        print(f"--- 块 {i} ---")
        print(f"📌 类型: {doc.metadata.get('type', 'unknown')}")
        print(f"📌 标题层级:")
        for level in range(1, 7):
            h = doc.metadata.get(f"H{level}", "")
            if h:
                print(f"   H{level}: {h}")
        print(f"📝 内容预览 ({len(doc.page_content)} 字符):")
        preview = doc.page_content[:200]
        if len(doc.page_content) > 200:
            preview += "..."
        print(f"   {preview}")
        print()

    return documents


def analyze_chunks(documents):
    """分析切分结果"""
    print("=" * 60)
    print("📈 切分分析")
    print("=" * 60)

    total = len(documents)
    normal_count = sum(1 for d in documents if d.metadata.get("type") == "normal")
    image_count = sum(1 for d in documents if d.metadata.get("type") == "image_description")

    avg_len = sum(len(d.page_content) for d in documents) / total if total > 0 else 0
    max_len = max(len(d.page_content) for d in documents) if documents else 0
    min_len = min(len(d.page_content) for d in documents) if documents else 0

    print(f"总块数: {total}")
    print(f"普通块: {normal_count}")
    print(f"图片描述块: {image_count}")
    print(f"平均长度: {avg_len:.1f} 字符")
    print(f"最大长度: {max_len} 字符")
    print(f"最小长度: {min_len} 字符")


if __name__ == "__main__":
    print("\n🚀 开始测试 MarkdownSemanticSplitter\n")

    docs1 = test_split_jinlongyu()
    analyze_chunks(docs1)

    print("\n")
    docs2 = test_split_email()
    analyze_chunks(docs2)

    print("\n✅ 测试完成!")
