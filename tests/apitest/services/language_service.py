"""
Language Service - Dynamic Language Support
"""
from typing import Dict, Any, Optional, Union
from enum import Enum
import json
import os
from contextlib import contextmanager

from config.settings import LanguageCode

class LanguageService:
    """Dynamic language service for API responses"""
    
    def __init__(self):
        self.language_data = self._load_language_data()
        self.current_language = LanguageCode.VIETNAMESE.value
        
    def _load_language_data(self) -> Dict[str, Any]:
        """Load language data from config"""
        try:
            # Get the correct path relative to the service file
            current_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(current_dir, "..", "config", "language.json")
            config_path = os.path.abspath(config_path)
            
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load language.json: {e}")
            return {}
    
    def set_language(self, language: Union[str, LanguageCode]) -> None:
        """Set current language"""
        if isinstance(language, LanguageCode):
            self.current_language = language.value
        else:
            self.current_language = language
    
    def get_language(self) -> str:
        """Get current language"""
        return self.current_language
    
    def get_supported_languages(self) -> list:
        """Get list of supported languages"""
        return [lang.value for lang in LanguageCode]
    
    def get_response_message(self, message_key: str, language: str = None, **kwargs) -> str:
        """Get localized response message with formatting"""
        lang = language or self.current_language
        
        # Get the message template
        message_template = (
            self.language_data
            .get("response_messages", {})
            .get(lang, {})
            .get(message_key, f"Missing message: {message_key}")
        )
        
        # Format the message with provided kwargs
        try:
            return message_template.format(**kwargs)
        except KeyError as e:
            print(f"Warning: Missing parameter {e} for message {message_key}")
            return message_template
    
    def get_error_message(self, error_key: str, language: str = None, **kwargs) -> str:
        """Get localized error message with formatting"""
        lang = language or self.current_language
        
        message_template = (
            self.language_data
            .get("error_messages", {})
            .get(lang, {})
            .get(error_key, f"Missing error: {error_key}")
        )
        
        try:
            return message_template.format(**kwargs)
        except KeyError as e:
            print(f"Warning: Missing parameter {e} for error {error_key}")
            return message_template
    
    def get_test_message(self, message_key: str, language: str = None, **kwargs) -> str:
        """Get localized test message with formatting"""
        lang = language or self.current_language
        
        message_template = (
            self.language_data
            .get("test_messages", {})
            .get(lang, {})
            .get(message_key, f"Missing test message: {message_key}")
        )
        
        try:
            return message_template.format(**kwargs)
        except KeyError as e:
            print(f"Warning: Missing parameter {e} for test message {message_key}")
            return message_template
    
    @contextmanager
    def language_context(self, language: str):
        """Context manager for temporary language switching"""
        old_language = self.current_language
        self.set_language(language)
        try:
            yield self
        finally:
            self.set_language(old_language)
    
    def validate_language(self, language: str) -> bool:
        """Validate if language is supported"""
        return language in self.get_supported_languages()
    
    def get_endpoint_info(self, endpoint_key: str, language: str = None) -> Dict[str, str]:
        """Get endpoint information (summary, description) for documentation"""
        lang = language or self.current_language
        
        return (
            self.language_data
            .get("app_content", {})
            .get(lang, {})
            .get("endpoints", {})
            .get(endpoint_key, {})
        )
    
    def get_app_content(self, language: str = None) -> Dict[str, Any]:
        """Get app content for documentation"""
        lang = language or self.current_language
        
        return (
            self.language_data
            .get("app_content", {})
            .get(lang, {})
        )

# Global language service instance
language_service = LanguageService()

# Helper function to get language from request
def get_request_language(request) -> str:
    """Extract language from request headers or query params"""
    # Try to get language from query parameters
    if hasattr(request, 'query_params') and 'lang' in request.query_params:
        lang = request.query_params['lang']
        if language_service.validate_language(lang):
            return lang
    
    # Try to get language from headers
    if hasattr(request, 'headers') and 'Accept-Language' in request.headers:
        accept_lang = request.headers['Accept-Language']
        # Simple parsing - just get the first language code
        if accept_lang:
            lang = accept_lang.split(',')[0].split('-')[0]
            if language_service.validate_language(lang):
                return lang
    
    # Default to current language
    return language_service.get_language() 