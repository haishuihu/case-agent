from functools import lru_cache

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ModelProfile(BaseModel):
    key: str
    label: str
    provider: str
    base_url: str
    api_key: str
    model_name: str
    # 上限由 Settings 与各供应商环境变量注入；此处仅为无配置时的兜底
    max_output_tokens: int = 131_072
    timeout_seconds: int = 120
    supports_vision: bool = False
    supports_structured_output: bool = True
    extra_body: dict[str, object] = Field(default_factory=dict)


class Settings(BaseSettings):
    app_name: str = "Internal Test Case Assistant"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./internal_testcase_assistant.db"

    default_model_key: str = "deepseek"

    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.2
    # OpenAI 兼容通道单次生成上限（具体模型仍以服务商为准，可能截断或报错）
    llm_max_tokens: int = 128_000
    llm_timeout_seconds: int = 60
    llm_supports_vision: bool = True

    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek-reasoner"
    # deepseek-reasoner 等可请求较高输出；deepseek-chat 等可能仅支持更低上限，可按模型在 .env 下调
    deepseek_max_output_tokens: int = 64_000
    deepseek_timeout_seconds: int = 120
    deepseek_supports_vision: bool = False
    deepseek_supports_structured_output: bool = True

    minimax_base_url: str = "https://api.minimaxi.com/v1"
    minimax_api_key: str = ""
    minimax_model: str = "MiniMax-M2.7-highspeed"
    # MiniMax 文档中 M2 等系列输出可达约 128k；超长请求由平台截断或拒绝
    minimax_max_output_tokens: int = 131_072
    minimax_timeout_seconds: int = 300
    minimax_supports_vision: bool = False
    minimax_supports_structured_output: bool = False

    embedding_base_url: str = ""
    embedding_api_key: str = ""
    embedding_model: str = "text-embedding-3-small"
    # 0 = 不传维度参数，由服务端默认（百炼多模态为 parameters.dimension；OpenAI 为 dimensions）
    # qwen3-vl-embedding 可选 2560/2048/1536/1024/768/512/256 等，索引与检索需一致
    embedding_dimensions: int = 0
    # 仅当模型名含 vl-embedding（如 qwen3-vl-embedding）时使用；国际站见百炼文档替换域名
    embedding_dashscope_multimodal_url: str = (
        "https://dashscope.aliyuncs.com/api/v1/services/embeddings/"
        "multimodal-embedding/multimodal-embedding"
    )

    max_upload_size_mb: int = 10
    max_document_chars_per_file: int = 8000
    max_total_document_chars: int = 20000
    max_upload_files: int = 6

    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        ]
    )

    frontend_dist_path: str = "frontend/dist"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    def get_model_profiles(self) -> dict[str, ModelProfile]:
        profiles = {
            "deepseek": ModelProfile(
                key="deepseek",
                label=f"DeepSeek ({self.deepseek_model})",
                provider="deepseek",
                base_url=self.deepseek_base_url,
                api_key=self.deepseek_api_key or self.llm_api_key,
                model_name=self.deepseek_model or self.llm_model,
                max_output_tokens=self.deepseek_max_output_tokens,
                timeout_seconds=self.deepseek_timeout_seconds,
                supports_vision=self.deepseek_supports_vision,
                supports_structured_output=self.deepseek_supports_structured_output,
            ),
            "minimax": ModelProfile(
                key="minimax",
                label=f"MiniMax ({self.minimax_model})",
                provider="minimax",
                base_url=self.minimax_base_url,
                api_key=self.minimax_api_key,
                model_name=self.minimax_model,
                max_output_tokens=self.minimax_max_output_tokens,
                timeout_seconds=self.minimax_timeout_seconds,
                supports_vision=self.minimax_supports_vision,
                supports_structured_output=self.minimax_supports_structured_output,
            ),
        }
        return profiles


@lru_cache
def get_settings() -> Settings:
    return Settings()
