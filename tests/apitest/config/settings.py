"""
OSC API Test Configuration Settings
"""
from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum
import os

class OSCTestEnvironment(Enum):
    """Test environment types"""
    DEVELOPMENT = "dev"
    STAGING = "staging"
    PRODUCTION = "prod"

class LanguageCode(Enum):
    """Supported language codes"""
    VIETNAMESE = "vi"
    ENGLISH = "en"
    JAPANESE = "ja"

@dataclass
class OSCServerConfig:
    """OSC Server configuration"""
    host: str = "127.0.0.1"
    port: int = 8000
    timeout: float = 5.0
    max_retries: int = 3
    
@dataclass
class TestConfig:
    """Test configuration settings"""
    environment: OSCTestEnvironment = OSCTestEnvironment.DEVELOPMENT
    osc_server: OSCServerConfig = OSCServerConfig()
    default_language: LanguageCode = LanguageCode.VIETNAMESE
    supported_languages: List[LanguageCode] = None
    test_data_path: str = "test/data"
    log_level: str = "INFO"
    
    def __post_init__(self):
        if self.supported_languages is None:
            self.supported_languages = [
                LanguageCode.VIETNAMESE,
                LanguageCode.ENGLISH,
                LanguageCode.JAPANESE
            ]

class TestSettings:
    """Test settings singleton"""
    _instance: Optional['TestSettings'] = None
    _config: Optional[TestConfig] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @property
    def config(self) -> TestConfig:
        if self._config is None:
            self._config = TestConfig()
        return self._config
    
    def update_config(self, **kwargs):
        """Update configuration values"""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
    
    def get_osc_url(self) -> str:
        """Get OSC server URL"""
        return f"http://{self.config.osc_server.host}:{self.config.osc_server.port}"

settings = TestSettings()
