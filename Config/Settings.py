"""Configuration settings for the research agent application."""

from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings."""
    
    # OpenAI
    openai_api_key: str
    embedding_model: str = "text-embedding-3-large"
    llm_model: str = "gpt-4.1"
    agent_temperature: float = 0.0
    
    # PostgreSQL
    postgres_user: str = "langchain"
    postgres_password: str = "langchain"
    postgres_db: str = "langchain-pgvector"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    
    # RAG Settings
    chunk_size: int = 2000
    chunk_overlap: int = 200
    collection_name: str = "research_documents"
    
    # Paths
    log_level: str = "INFO"
    audit_log_path: str = "./audit_logs"
    export_path: str = "./exports"
    documents_path: str = "./documents"
    
    # Agent
    max_iterations: int = 10
    
    @property
    def database_url(self) -> str:
        """Get PostgreSQL connection string."""
        return (
            "postgresql://langchain:langchain@localhost:5432/langchain"
        )
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()