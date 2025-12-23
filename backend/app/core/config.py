"""Application configuration using pydantic-settings."""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database
    database_url: str = "postgresql://user:password@localhost:5432/switch_impact"
    
    # SEC Thailand API Keys
    sec_fund_factsheet_api_key: str = ""
    sec_fund_daily_info_api_key: str = ""
    
    # API Settings
    api_page_size: int = 25
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
