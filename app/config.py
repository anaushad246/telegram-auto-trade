import os
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator

class Settings(BaseSettings):
    # Telegram
    API_ID: int = Field(..., description="Telegram API ID")
    API_HASH: str = Field(..., description="Telegram API Hash")
    PHONE: str = Field(..., description="Telegram Phone Number")
    GROUP_NAMES: List[str] = Field(default_factory=list, description="List of group names to listen to (optional, for display)")
    
    # MetaTrader 5
    MT5_LOGIN: int = Field(..., description="MT5 Login ID")
    MT5_PASSWORD: str = Field(..., description="MT5 Password")
    MT5_SERVER: str = Field(..., description="MT5 Server Name")
    MT5_PATH: str = Field(r"C:\Program Files\MetaTrader 5\terminal64.exe", description="Path to MT5 terminal64.exe")
    
    # AI & Trading
    # CHANGE THESE FIELDS
    OPENROUTER_API_KEY: str = Field(..., description="OpenRouter API Key (Supports DeepSeek, Chimera, etc.)")
    # Change the default value here
    OPENROUTER_MODEL: str = Field("tngtech/deepseek-r1t2-chimera:free", description="Model to use via OpenRouter...")
    # GEMINI_API_KEY: str = Field(..., description="Google Gemini API Key")
    FIXED_LOT_SIZE: float = Field(0.01, description="Fixed lot size for trades")
    
    # Magic Map (could be loaded from file, but keeping simple for now)
    # We will load this from a separate JSON or keep it here if static enough.
    # For now, let's keep the map logic in the service or here. 
    # Let's define it here as a constant or field if it was in config.py before.
    # The previous code had it in telegram_listener.py. We'll move it to a service or a separate file.
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator("GROUP_NAMES", mode="before")
    @classmethod
    def parse_group_names(cls, v):
        if isinstance(v, str):
            return [g.strip() for g in v.split(',') if g.strip()]
        return v

# Global instance
try:
    config = Settings()
    print("✅ [Config] Configuration loaded successfully.")
except Exception as e:
    print(f"❌ [Config] Failed to load configuration: {e}")
    raise
