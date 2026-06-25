"""
Configuration management for Video-to-Action.
Uses pydantic-settings to load config from environment variables and .env file.
"""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""
    
    # MySQL Database settings
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = ""
    MYSQL_DATABASE: str = "video_to_action"
    MYSQL_POOL_SIZE: int = 10
    
    # Application settings
    DEBUG: bool = False
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    # LLM settings
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_BASE_URL: Optional[str] = None
    
    # Download settings
    DOWNLOAD_DIR: str = "./data/videos"
    MAX_CONCURRENT_DOWNLOADS: int = 3
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get settings instance (singleton)."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
