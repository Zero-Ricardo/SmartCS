from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """应用配置"""

    # 服务配置
    app_name: str = "SmartCS AI Engine"
    debug: bool = False

    # 数据库配置 (使用 psycopg 异步驱动)
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/smartcs"

    # 服务间鉴权密钥
    internal_secret: str = "your-internal-secret-key"

    # LLM 配置
    openai_api_key: Optional[str] = None
    openai_api_base: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"

    # 多模型配置（不同节点使用不同模型）
    fast_model: str = "qwen-turbo"        # 轻量模型：analyze_node
    quality_model: str = "qwen-turbo"     # 强力模型：generate_node

    # rag的嵌入模型配置
    embedding_api_base : str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    embedding_model : str = "text-embedding-v4"

    # Qdrant 向量数据库配置
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "pxb"  # 向量数据集合名称

    # JWT 认证配置
    jwt_secret_key: str = "smartcs-super-secret-key-2026"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24小时

    # 文件上传配置
    upload_dir: str = "./uploads"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",  # 忽略未定义的环境变量
    }


settings = Settings()
