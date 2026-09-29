import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv(Path(__file__).resolve().parents[1] / '.env')


class Settings(BaseSettings):
    APP_NAME: str = 'SupportMind'
    DATABASE_URL: str = 'sqlite:///./supportmind.db'
    GROQ_API_KEY: str = ''
    GROQ_MODEL: str = 'openai/gpt-oss-120b'
    HINDSIGHT_URL: str = ''
    HINDSIGHT_API_KEY: str = ''
    HINDSIGHT_DEFAULT_BANK: str = 'customer'
    JWT_SECRET: str = ''
    ADMIN_EMAIL: str = ''
    ADMIN_PASSWORD: str = ''
    FRONTEND_URL: str = 'http://localhost:5173'

    model_config = SettingsConfigDict(env_file='.env', extra='ignore')


@lru_cache
def get_settings() -> Settings:
    return Settings()
