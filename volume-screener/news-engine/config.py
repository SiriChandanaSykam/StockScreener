"""
Configuration management for News Intelligence Engine.
Supports environment variables and sensible defaults.
"""

import os
from dataclasses import dataclass, field
from typing import List
from pathlib import Path


@dataclass
class ScraperConfig:
    """Configuration for web scrapers."""
    request_timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    rate_limit_per_minute: int = 30
    
    # User agents to rotate (avoid blocking)
    user_agents: List[str] = field(default_factory=lambda: [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ])


@dataclass
class DatabaseConfig:
    """Database configuration."""
    # Default to SQLite for easy setup; can switch to PostgreSQL
    database_url: str = field(default_factory=lambda: os.getenv(
        "NEWS_ENGINE_DB_URL",
        f"sqlite:///{Path(__file__).parent / 'data' / 'news_v4.db'}"
    ))
    echo_sql: bool = False


@dataclass
class RedisConfig:
    """Redis configuration for caching and Celery."""
    host: str = field(default_factory=lambda: os.getenv("REDIS_HOST", "localhost"))
    port: int = field(default_factory=lambda: int(os.getenv("REDIS_PORT", "6379")))
    db: int = 0
    
    @property
    def url(self) -> str:
        return f"redis://{self.host}:{self.port}/{self.db}"


@dataclass
class Config:
    """Main configuration container."""
    # Environment
    env: str = field(default_factory=lambda: os.getenv("NEWS_ENGINE_ENV", "development"))
    debug: bool = field(default_factory=lambda: os.getenv("NEWS_ENGINE_DEBUG", "true").lower() == "true")
    
    # Sub-configs
    scraper: ScraperConfig = field(default_factory=ScraperConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)
    
    # Paths
    base_dir: Path = field(default_factory=lambda: Path(__file__).parent)
    data_dir: Path = field(default_factory=lambda: Path(__file__).parent / "data")
    
    def __post_init__(self):
        """Ensure data directory exists."""
        self.data_dir.mkdir(parents=True, exist_ok=True)


# Global config instance
config = Config()
