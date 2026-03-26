FROM swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/python:3.12-slim

WORKDIR /app

# 安装 curl（健康检查需要）和 uv
RUN pip install uv

# 只复制依赖文件
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

# 复制源代码
COPY . .

# 运行
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
