"""
Configuration management for Agentic Compliance Auditor
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List
import os
from pathlib import Path


class Settings(BaseSettings):
    """Application settings"""

    # Project paths
    BASE_DIR: Path = Path(__file__).parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    LOGS_DIR: Path = BASE_DIR / "logs"

    # LLM Configuration (OpenAI)
    OPENAI_API_KEY: str = Field(default="")
    OPENAI_MODEL: str = Field(default="gpt-4o-mini")
    OPENAI_BASE_URL: str = Field(default="https://api.openai.com/v1")
    OPENAI_TEMPERATURE: float = Field(default=0.1)

    # Vector Database
    CHROMA_PERSIST_DIR: str = Field(default=str((Path(__file__).parent.parent / "data" / "chroma_db").resolve()))
    EMBEDDING_MODEL: str = Field(default="text-embedding-3-small")

    # Memory Systems
    REDIS_HOST: str = Field(default="localhost")
    REDIS_PORT: int = Field(default=6379)
    REDIS_DB: int = Field(default=0)

    # API Configuration
    API_HOST: str = Field(default="0.0.0.0")
    API_PORT: int = Field(default=8000)
    API_WORKERS: int = Field(default=4)

    # Logging
    LOG_LEVEL: str = Field(default="INFO")
    LOG_FILE: str = Field(default=str((Path(__file__).parent.parent / "logs" / "app.log").resolve()))

    # Retrieval Configuration
    TOP_K_RESULTS: int = Field(default=5)
    CHUNK_SIZE: int = Field(default=512)
    CHUNK_OVERLAP: int = Field(default=50)
    RERANK_ENABLED: bool = Field(default=False)

    # Agent Configuration
    MAX_ITERATIONS: int = Field(default=3)
    AGENT_TIMEOUT: int = Field(default=300)
    ENABLE_SELF_REFLECTION: bool = Field(default=False)

    # Evaluation
    EVAL_DATASET_PATH: str = Field(default=str((Path(__file__).parent.parent / "data" / "eval_dataset.json").resolve()))
    RAGAS_METRICS: str = Field(default="faithfulness,answer_relevancy,context_precision,context_recall")

    class Config:
        env_file = ".env"
        case_sensitive = True

    def get_ragas_metrics(self) -> List[str]:
        """Parse RAGAS metrics from comma-separated string"""
        return [m.strip() for m in self.RAGAS_METRICS.split(",")]

    def ensure_dirs(self):
        """Create necessary directories if they don't exist"""
        dirs = [
            self.DATA_DIR,
            self.DATA_DIR / "raw",
            self.DATA_DIR / "processed",
            self.DATA_DIR / "sample_docs",
            self.LOGS_DIR,
            Path(self.CHROMA_PERSIST_DIR),
        ]
        for dir_path in dirs:
            dir_path.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()
settings.ensure_dirs()
