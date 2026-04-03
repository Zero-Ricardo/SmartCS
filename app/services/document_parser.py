"""
文档解析服务（轻量级本地解析）
- PDF: 使用 pymupdf4llm 转换为 Markdown
- DOCX: 使用 python-docx 提取文本
"""
import pymupdf4llm
from docx import Document


def parse_pdf_to_md(file_path: str) -> str:
    """
    极其轻量的 PDF 转 Markdown

    Args:
        file_path: PDF 文件路径

    Returns:
        Markdown 格式的文本内容
    """
    # pymupdf4llm 会自动处理表格、图片描述，并按 Markdown 格式输出
    md_text = pymupdf4llm.to_markdown(file_path)
    return md_text


def parse_docx_to_md(file_path: str) -> str:
    """
    简单的 Word 转纯文本

    Args:
        file_path: DOCX 文件路径

    Returns:
        纯文本内容
    """
    doc = Document(file_path)
    paragraphs = [paragraph.text for paragraph in doc.paragraphs if paragraph.text.strip()]
    return "\n\n".join(paragraphs)


def parse_file_to_md(file_path: str, file_type: str) -> str:
    """
    根据文件类型解析为 Markdown

    Args:
        file_path: 文件路径
        file_type: 文件类型 (pdf/docx/txt)

    Returns:
        Markdown 格式的文本内容
    """
    if file_type == "pdf":
        return parse_pdf_to_md(file_path)
    elif file_type == "docx":
        return parse_docx_to_md(file_path)
    elif file_type == "txt":
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    else:
        raise ValueError(f"不支持的文件类型: {file_type}")
