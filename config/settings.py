"""Application configuration"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration"""
    
    # LLM Configuration
    LLM_API_URL = os.getenv("LLM_API_URL", "http://localhost:11434")
    LLM_MODEL = os.getenv("LLM_MODEL", "llama2")
    LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", 0.7))
    
    # LinkedIn Configuration
    LINKEDIN_USERNAME = os.getenv("LINKEDIN_USERNAME")
    LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD")
    LINKEDIN_ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN")
    
    # Scheduler Configuration
    SCHEDULE_INTERVAL_HOURS = int(os.getenv("SCHEDULE_INTERVAL_HOURS", 24))
    SCHEDULE_START_TIME = os.getenv("SCHEDULE_START_TIME", "09:00")
    
    # Storage Configuration
    DATABASE_PATH = os.getenv("DATABASE_PATH", "data/database.db")
    POSTS_OUTPUT_DIR = os.getenv("POSTS_OUTPUT_DIR", "data/posts")
    
    # Logging Configuration
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False


def get_config():
    """Get configuration based on environment"""
    env = os.getenv("ENVIRONMENT", "development")
    if env == "production":
        return ProductionConfig()
    return DevelopmentConfig()
