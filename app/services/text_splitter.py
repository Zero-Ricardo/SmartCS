"""
语义文本分割器

基于 Markdown 标题结构进行语义化切分，保留完整的层级信息作为 Metadata
"""
import re
from typing import List, Dict, Any, Optional
from langchain_core.documents import Document


class MarkdownSemanticSplitter:
    """
    Markdown 语义分割器

    核心思想：
    1. 按 Markdown 标题层级（H1-H6）进行结构化切分
    2. 每个切分块都携带父级标题作为 Metadata
    3. 图片描述块（> 🖼）作为独立块处理
    4. 超长正文进行二次细切，但保留所有 Metadata
    5. 可选：在 chunk 内容前注入标题前缀，增强语义检索
    """

    def __init__(
        self,
        chunk_size: int = 800,
        chunk_overlap: int = 100,
        min_chunk_size: int = 30,
        inject_title_prefix: bool = True,  # 是否注入标题前缀
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        self.inject_title_prefix = inject_title_prefix

    def _build_title_prefix(self, headings: Dict[int, str], doc_title: str = "") -> str:
        """
        构建标题前缀

        Args:
            headings: 标题层级字典 {1: "H1内容", 2: "H2内容", ...}
            doc_title: 文档标题

        Returns:
            标题前缀字符串，如 "【文档标题 > H2 > H3】"
        """
        parts = []

        # 添加文档标题
        if doc_title:
            # 清理文件名中的扩展名
            title = doc_title.replace(".md", "")
            parts.append(title)

        # 添加有内容的标题层级
        for level in range(1, 7):
            h = headings.get(level, "")
            if h:
                parts.append(h)

        if parts:
            return "【" + " > ".join(parts) + "】\n"
        return ""

    def split_text(self, text: str, source: str = "", doc_title: str = "") -> List[Document]:
        """
        分割文本

        Args:
            text: Markdown 文本
            source: 原文链接
            doc_title: 文档标题

        Returns:
            List[Document]: 切分后的文档列表
        """
        documents = []

        # 按行解析
        lines = text.split("\n")
        current_headings: Dict[int, str] = {}
        current_content_lines: List[str] = []
        current_image_lines: Optional[List[str]] = None

        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # 检测 Markdown 标题
            heading_match = re.match(r"^(#{1,6})\s+(.+)$", stripped)

            if heading_match:
                # 保存之前的图片块
                if current_image_lines is not None:
                    doc = self._create_image_document(
                        current_image_lines, source, doc_title, current_headings
                    )
                    if doc:
                        documents.append(doc)
                    current_image_lines = None

                # 保存之前的内容
                if current_content_lines:
                    docs = self._split_content(
                        current_content_lines, source, doc_title, current_headings
                    )
                    documents.extend(docs)
                    current_content_lines = []

                # 更新当前标题
                level = len(heading_match.group(1))
                heading_text = heading_match.group(2).strip()
                # 清理标题中的特殊格式
                heading_text = re.sub(r"\*+", "", heading_text)

                current_headings[level] = heading_text
                # 清除更低级别的标题
                current_headings = {
                    k: v for k, v in current_headings.items() if k <= level
                }

                i += 1
                continue

            # 检测图片描述块
            if stripped.startswith("> ") or stripped.startswith(">") or "> 🖼" in stripped:
                # 保存之前的内容
                if current_content_lines:
                    docs = self._split_content(
                        current_content_lines, source, doc_title, current_headings
                    )
                    documents.extend(docs)
                    current_content_lines = []

                # 开始收集图片块
                current_image_lines = [stripped]
                # 继续收集图片块的后续行
                i += 1
                while i < len(lines):
                    next_line = lines[i].strip()
                    if not next_line:
                        i += 1
                        continue
                    # 图片块结束：遇到新标题或非图片行
                    if re.match(r"^(#{1,6})\s+", next_line):
                        break
                    if not (next_line.startswith(">") or "> 🖼" in next_line or next_line.startswith("**")):
                        break
                    current_image_lines.append(next_line)
                    i += 1

                # 处理图片块
                if current_image_lines:
                    doc = self._create_image_document(
                        current_image_lines, source, doc_title, current_headings
                    )
                    if doc:
                        documents.append(doc)
                    current_image_lines = None
                continue

            # 普通内容行
            if stripped:
                current_content_lines.append(stripped)

            i += 1

        # 处理最后剩余的内容
        if current_image_lines is not None:
            doc = self._create_image_document(
                current_image_lines, source, doc_title, current_headings
            )
            if doc:
                documents.append(doc)

        if current_content_lines:
            docs = self._split_content(
                current_content_lines, source, doc_title, current_headings
            )
            documents.extend(docs)

        return documents

    def _create_image_document(
        self,
        image_lines: List[str],
        source: str,
        doc_title: str,
        headings: Dict[int, str],
    ) -> Optional[Document]:
        """创建图片描述文档"""
        content = "\n".join(image_lines)
        if len(content) < self.min_chunk_size:
            return None

        metadata = self._build_metadata(source, doc_title, headings)
        metadata["type"] = "image_description"

        # 注入标题前缀
        if self.inject_title_prefix:
            prefix = self._build_title_prefix(headings, doc_title)
            content = prefix + content

        return Document(page_content=content, metadata=metadata)

    def _split_content(
        self,
        content_lines: List[str],
        source: str,
        doc_title: str,
        headings: Dict[int, str],
    ) -> List[Document]:
        """分割内容，可能需要二次切分"""
        content = "\n".join(content_lines)
        if not content.strip():
            return []

        metadata = self._build_metadata(source, doc_title, headings)
        metadata["type"] = "normal"

        # 注入标题前缀
        if self.inject_title_prefix:
            prefix = self._build_title_prefix(headings, doc_title)
            content = prefix + content

        # 如果内容不长，直接返回
        if len(content) <= self.chunk_size:
            return [Document(page_content=content, metadata=metadata)]

        # 需要二次切分
        return self._fallback_split(content, metadata)

    def _fallback_split(
        self,
        content: str,
        metadata: Dict[str, Any],
    ) -> List[Document]:
        """二次切分（按段落，保留 metadata）"""
        documents = []
        paragraphs = re.split(r"\n\n+", content)
        current_chunk = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # 如果单个段落就超过 chunk_size
            if len(para) > self.chunk_size:
                # 保存当前 chunk
                if current_chunk.strip():
                    documents.append(
                        Document(page_content=current_chunk.strip(), metadata=metadata.copy())
                    )
                    # 保留重叠部分
                    current_chunk = current_chunk[-self.chunk_overlap :]

                # 按句子切分大段落
                sentences = self._split_sentences(para)
                for sentence in sentences:
                    if not sentence.strip():
                        continue

                    if len(current_chunk) + len(sentence) <= self.chunk_size:
                        current_chunk += sentence + "\n"
                    else:
                        if current_chunk.strip():
                            documents.append(
                                Document(page_content=current_chunk.strip(), metadata=metadata.copy())
                            )
                        # 保留重叠部分
                        current_chunk = current_chunk[-self.chunk_overlap :] + sentence + "\n"
            else:
                if len(current_chunk) + len(para) <= self.chunk_size:
                    current_chunk += para + "\n\n"
                else:
                    if current_chunk.strip():
                        documents.append(
                            Document(page_content=current_chunk.strip(), metadata=metadata.copy())
                        )
                    # 保留重叠部分
                    current_chunk = current_chunk[-self.chunk_overlap :] + para + "\n\n"

        # 保存最后一个 chunk
        if current_chunk.strip():
            documents.append(
                Document(page_content=current_chunk.strip(), metadata=metadata.copy())
            )

        return documents

    # def _split_sentences(self, text: str) -> List[str]:
    #     """按句子切分"""
    #     sentences = re.split(r"([。！？.!?\n])", text)
    #     merged = []
    #     for i in range(0, len(sentences) - 1, 2):
    #         if i + 1 < len(sentences):
    #             merged.append(sentences[i] + sentences[i + 1])
    #         else:
    #             merged.append(sentences[i])
    #     return merged
    
    def _split_sentences(self, text: str) -> List[str]:
        """按句子切分"""
        # 使用捕获组保留分隔符
        sentences = re.split(r"([。！？.!?\n])", text)
        merged = []
        # 遍历时步长为2，处理文本和紧跟的标点
        for i in range(0, len(sentences), 2):
            chunk = sentences[i]
            # 如果后面还有元素，说明是标点符号，加上它
            if i + 1 < len(sentences):
                chunk += sentences[i + 1]
            if chunk.strip(): # 过滤掉纯空白的无效块
                merged.append(chunk)
        return merged

    def _build_metadata(
        self,
        source: str,
        doc_title: str,
        headings: Dict[int, str],
    ) -> Dict[str, Any]:
        """构建元数据"""
        metadata = {
            "source": source,
            "doc_title": doc_title,
            "type": "normal",
        }

        # 添加各层级标题
        for level in range(1, 7):
            key = f"H{level}"
            metadata[key] = headings.get(level, "")

        return metadata


# 全局实例
text_splitter = MarkdownSemanticSplitter(chunk_size=800, chunk_overlap=100)
