FROM python:3.12-slim

WORKDIR /app

# 安装系统依赖：pymupdf4llm、fastembed 等需要的 C 库
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安装 uv
RUN pip install uv

# 只复制依赖文件
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

# 复制源代码
COPY . .

# 运行
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
