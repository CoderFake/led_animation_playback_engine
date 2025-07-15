"""
OSC Message Factory - Factory Pattern Implementation
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import json
import os

from config.settings import settings, LanguageCode
from dataclass.osc_models import OSCRequest, OSCMessageType, OSCDataType

class MessageFactory(ABC):
    """Abstract message factory"""
    
    @abstractmethod
    def create_message(self, **kwargs) -> OSCRequest:
        """Create OSC message"""
        pass

class PaletteMessageFactory(MessageFactory):
    """Factory for palette messages"""
    
    def create_message(self, palette_id: str, color_id: int, r: int, g: int, b: int) -> OSCRequest:
        """Create palette color message"""
        
        # Validate inputs
        if palette_id not in ['A', 'B', 'C', 'D', 'E']:
            raise ValueError(f"Invalid palette_id: {palette_id}. Must be A-E")
        
        if not (0 <= color_id <= 5):
            raise ValueError(f"Invalid color_id: {color_id}. Must be 0-5")
        
        for color_val, color_name in [(r, 'r'), (g, 'g'), (b, 'b')]:
            if not (0 <= color_val <= 255):
                raise ValueError(f"Invalid {color_name} value: {color_val}. Must be 0-255")
        
        # Create request - simple OSC message
        request = OSCRequest()
        request.set_address(f"/palette/{palette_id}/{color_id}")
        request.set_message_type(OSCMessageType.COLOR)
        
        # Add RGB parameters
        request.add_parameter("r", r, OSCDataType.INT, "Red component")
        request.add_parameter("g", g, OSCDataType.INT, "Green component")
        request.add_parameter("b", b, OSCDataType.INT, "Blue component")
        
        # Add metadata
        request.add_metadata("palette_id", palette_id)
        request.add_metadata("color_id", color_id)
        request.add_metadata("factory", "PaletteMessageFactory")
        
        return request

class GenericMessageFactory(MessageFactory):
    """Factory for generic messages"""
    
    def create_message(self, address: str, message_type: OSCMessageType = OSCMessageType.LED_CONTROL,
                      parameters: List[Dict[str, Any]] = None) -> OSCRequest:
        """Create generic OSC message"""
        
        request = OSCRequest()
        request.set_address(address)
        request.set_message_type(message_type)
        
        # Add parameters if provided
        if parameters:
            for param in parameters:
                request.add_parameter(
                    param.get("name", ""),
                    param.get("value", None),
                    OSCDataType(param.get("data_type", "string")),
                    param.get("description", "")
                )
        
        request.add_metadata("factory", "GenericMessageFactory")
        return request

class MultiLanguageMessageFactory:
    """Factory supporting multiple languages for UI, simple OSC messages"""
    
    def __init__(self):
        self.language_data = self._load_language_data()
        self.factories = {
            "palette": PaletteMessageFactory(),
            "generic": GenericMessageFactory()
        }
    
    def _load_language_data(self) -> Dict[str, Any]:
        """Load language data from config"""
        try:
            config_path = os.path.abspath("test/apitest/config/language.json")
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load language.json: {e}")
            return {}
    
    def get_factory(self, factory_type: str) -> MessageFactory:
        """Get factory by type"""
        return self.factories.get(factory_type, self.factories["generic"])
    
    def create_palette_message(self, palette_id: str, color_id: int, r: int, g: int, b: int) -> OSCRequest:
        """Create simple palette OSC message"""
        factory = self.get_factory("palette")
        return factory.create_message(palette_id, color_id, r, g, b)
    
    def create_test_message(self, address: str, test_type: str = "endpoint_test") -> OSCRequest:
        """Create test message"""
        factory = self.get_factory("generic")
        return factory.create_message(address, OSCMessageType.STATUS, [])
    
    def get_supported_languages(self) -> List[str]:
        """Get list of supported languages"""
        return list(self.language_data.get("test_messages", {}).keys())
    
    def get_test_message(self, key: str, language: str = "vi") -> str:
        """Get localized test message for UI"""
        return self.language_data.get("test_messages", {}).get(language, {}).get(key, key)

message_factory = MultiLanguageMessageFactory() 