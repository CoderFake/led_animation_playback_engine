"""
Centralized validation utilities for LED Animation Engine
Eliminates duplicate validation code and provides consistent error handling
"""

from typing import Any, List, Union, Tuple, Optional, Dict
from .logger import setup_logger

try:
    from config.settings import EngineSettings
    settings = EngineSettings
except ImportError:
    settings = None

class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass

class ValidationUtils:
    """Centralized validation utilities"""
    
    PALETTE_INDEX_RANGE = (0, 5)        
    TRANSPARENCY_RANGE = (0.0, 1.0)       
    
    @staticmethod
    def get_brightness_range():
        """Get brightness range from settings"""
        return (0, 255)  
    
    @staticmethod
    def get_speed_range():
        """Get speed range from settings"""
        if settings:
            return (0, settings.ANIMATION.speed_range_max)
        return (0, 1023)
    
    @staticmethod
    def get_default_led_count_range():
        """Get default LED count range from settings (for config validation)"""
        if settings:
            return (1, 10000000)
        return (1, 10000000)
    
    @staticmethod
    def get_fps_range():
        """Get FPS range from settings"""
        if settings:
            return (1, 240)  
        return (1, 240)
    
    @staticmethod
    def validate_led_count_flexible(led_count: int, max_override: int = None) -> bool:
        """Validate LED count với khả năng override max từ scene JSON"""
        if not isinstance(led_count, int) or led_count < 1:
            return False
        
        if max_override is not None:
            return led_count <= max_override
        
        default_range = ValidationUtils.get_default_led_count_range()
        return led_count <= default_range[1]
    
    BRIGHTNESS_RANGE = get_brightness_range.__func__()
    SPEED_RANGE = get_speed_range.__func__()
    POSITION_RANGE = (-1000000, 1000000)  
    MAX_SEGMENT_ID = 99999                
    MAX_SCENE_ID = 9999                   
    MAX_EFFECT_ID = 9999               
    MAX_PALETTE_ID = 99               
    
    @staticmethod
    def validate_int(value: Any, min_val: int = None, max_val: int = None, 
                    field_name: str = "value") -> bool:
        """Validate integer value with optional range checking"""
        if not isinstance(value, int):
            return False
        if min_val is not None and value < min_val:
            return False
        if max_val is not None and value > max_val:
            return False
        return True
    
    @staticmethod
    def validate_float(value: Any, min_val: float = None, max_val: float = None,
                      field_name: str = "value") -> bool:
        """Validate float value with optional range checking"""
        if not isinstance(value, (int, float)):
            return False
        if min_val is not None and value < min_val:
            return False
        if max_val is not None and value > max_val:
            return False
        return True
    
    @staticmethod
    def validate_list(value: Any, expected_type: type = None, 
                     min_length: int = None, max_length: int = None,
                     field_name: str = "list") -> bool:
        """Validate list with optional type and length checking"""
        if not isinstance(value, list):
            return False
        if min_length is not None and len(value) < min_length:
            return False
        if max_length is not None and len(value) > max_length:
            return False
        if expected_type is not None:
            if not all(isinstance(item, expected_type) for item in value):
                return False
        return True
    
    @staticmethod
    def validate_color_indices(colors: List[int]) -> bool:
        """Validate color indices (palette indices 0-5)"""
        if not ValidationUtils.validate_list(colors, int, min_length=1):
            return False
        return all(ValidationUtils.validate_int(c, *ValidationUtils.PALETTE_INDEX_RANGE) 
                  for c in colors)
    
    @staticmethod
    def validate_transparency_values(transparencies: List[float]) -> bool:
        """Validate transparency values (0.0-1.0)"""
        if not ValidationUtils.validate_list(transparencies, (int, float), min_length=1):
            return False
        return all(ValidationUtils.validate_float(t, *ValidationUtils.TRANSPARENCY_RANGE) 
                  for t in transparencies)
    
    @staticmethod
    def validate_length_values(lengths: List[int]) -> bool:
        """Validate length values (positive integers) - flexible upper limit"""
        if not ValidationUtils.validate_list(lengths, int, min_length=1):
            return False
        return all(ValidationUtils.validate_int(l, 0) for l in lengths)
    
    def validate_move_range(move_range: List[float], led_count_context: int = None) -> bool:
        """Validate move range với context từ scene hiện tại"""
        if not ValidationUtils.validate_list(move_range, (int, float), min_length=2, max_length=2):
            return False
        min_pos, max_pos = move_range[0], move_range[1]
        
        if min_pos == 0 and max_pos == 0:
            return True
            
        if min_pos > max_pos:
            return False
        if min_pos < 0 or max_pos < 0:
            return False
        
        if led_count_context is not None:
            return max_pos <= led_count_context
        
        default_range = ValidationUtils.get_default_led_count_range()
        return max_pos <= default_range[1]
    
    @staticmethod
    def validate_dimmer_time(dimmer_time: List[List[float]]) -> bool:
        """Validate dimmer time transitions - time-based format from specs"""
        if not ValidationUtils.validate_list(dimmer_time):
            return False
        for transition in dimmer_time:
            if not ValidationUtils.validate_list(transition, (int, float), min_length=3, max_length=3):
                return False
            duration, start_brightness, end_brightness = transition
            if duration <= 0:
                return False
            if not (ValidationUtils.validate_float(start_brightness, 0, 100) and
                   ValidationUtils.validate_float(end_brightness, 0, 100)):
                return False
        return True
    
    @staticmethod
    def validate_rgb_color(color: Any) -> bool:
        """Validate RGB color (3-element list/tuple with 0-255 values)"""
        if not isinstance(color, (list, tuple)) or len(color) < 3:
            return False
        return all(ValidationUtils.validate_int(c, 0, 255) for c in color[:3])
    
    @staticmethod
    def validate_osc_address(address: str) -> bool:
        """Validate OSC address format"""
        if not isinstance(address, str) or not address.startswith('/'):
            return False
        return len(address) > 1 and all(c.isalnum() or c in '/_-' for c in address[1:])
    
    @staticmethod
    def validate_json_structure(data: Dict, required_keys: List[str]) -> bool:
        """Validate JSON structure has required keys"""
        if not isinstance(data, dict):
            return False
        return all(key in data for key in required_keys)
    
    @staticmethod
    def validate_scene_id(scene_id: int) -> bool:
        """Validate scene ID (0-origin)"""
        return ValidationUtils.validate_int(scene_id, 0, ValidationUtils.MAX_SCENE_ID)
    
    @staticmethod
    def validate_effect_id(effect_id: int) -> bool:
        """Validate effect ID (0-origin)"""
        return ValidationUtils.validate_int(effect_id, 0, ValidationUtils.MAX_EFFECT_ID)
    
    @staticmethod
    def validate_palette_id(palette_id: int) -> bool:
        """Validate palette ID (0-origin)"""
        return ValidationUtils.validate_int(palette_id, 0, ValidationUtils.MAX_PALETTE_ID)
    
    @staticmethod
    def validate_led_count(led_count: int, max_override: int = None) -> bool:
        """Validate LED count với flexible approach"""
        return ValidationUtils.validate_led_count_flexible(led_count, max_override)
    
    @staticmethod
    def validate_fps(fps: int) -> bool:
        """Validate FPS value - configurable as per specs"""
        fps_range = ValidationUtils.get_fps_range()
        return ValidationUtils.validate_int(fps, fps_range[0], fps_range[1])
    
    @staticmethod
    def validate_speed_percent(speed_percent: int) -> bool:
        """Validate speed percentage (0-1023% as per specs)"""
        speed_range = ValidationUtils.get_speed_range()
        return ValidationUtils.validate_int(speed_percent, speed_range[0], speed_range[1])
    
    @staticmethod
    def validate_master_brightness(brightness: int) -> bool:
        """Validate master brightness (0-255 as per specs)"""
        brightness_range = ValidationUtils.get_brightness_range()
        return ValidationUtils.validate_int(brightness, brightness_range[0], brightness_range[1])

class DataSanitizer:
    """Centralized data sanitization utilities"""
    
    @staticmethod
    def sanitize_int(value: Any, default: int = 0, min_val: int = None, max_val: int = None) -> int:
        """Sanitize integer value with bounds checking"""
        try:
            result = int(value)
            if min_val is not None:
                result = max(min_val, result)
            if max_val is not None:
                result = min(max_val, result)
            return result
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def sanitize_float(value: Any, default: float = 0.0, min_val: float = None, max_val: float = None) -> float:
        """Sanitize float value with bounds checking"""
        try:
            result = float(value)
            if min_val is not None:
                result = max(min_val, result)
            if max_val is not None:
                result = min(max_val, result)
            return result
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def sanitize_list(value: Any, default: List = None, expected_type: type = None) -> List:
        """Sanitize list value"""
        if default is None:
            default = []
        
        if not isinstance(value, list):
            return default.copy()
        
        if expected_type is None:
            return value
        
        sanitized = []
        for item in value:
            if isinstance(item, expected_type):
                sanitized.append(item)
        
        return sanitized if sanitized else default.copy()
    
    @staticmethod
    def sanitize_color_indices(colors: List[int]) -> List[int]:
        """Sanitize color indices to valid palette range"""
        if not isinstance(colors, list) or not colors:
            return [0]
        
        sanitized = []
        for color in colors:
            sanitized.append(DataSanitizer.sanitize_int(
                color, 0, *ValidationUtils.PALETTE_INDEX_RANGE
            ))
        
        return sanitized if sanitized else [0]
    
    @staticmethod
    def sanitize_transparency_values(transparencies: List[float], target_length: int) -> List[float]:
        """Sanitize transparency values to match target length"""
        if not isinstance(transparencies, list):
            return [1.0] * target_length
        
        sanitized = []
        for t in transparencies:
            sanitized.append(DataSanitizer.sanitize_float(
                t, 0.0, *ValidationUtils.TRANSPARENCY_RANGE
            ))
        
        while len(sanitized) < target_length:
            sanitized.append(0.0)
        
        return sanitized[:target_length]
    
    @staticmethod
    def sanitize_length_values(lengths: List[int], target_length: int) -> List[int]:
        """Sanitize length values - flexible upper limit"""
        if not isinstance(lengths, list):
            return [1] * target_length
        
        sanitized = []
        for l in lengths:
            sanitized.append(DataSanitizer.sanitize_int(l, 1, 0))
        
        while len(sanitized) < target_length:
            sanitized.append(1)
        
        return sanitized[:target_length]
    
    @staticmethod
    def sanitize_move_range(move_range: List[float], led_count: int = 225) -> List[float]:
        """Sanitize move range"""
        if not isinstance(move_range, list) or len(move_range) < 2:
            return [0.0, float(max(1, led_count - 1))]
        
        min_pos = move_range[0]
        max_pos = move_range[1]
        
        if min_pos == 0 and max_pos == 0:
            return [0.0, 0.0]
        
        min_pos = DataSanitizer.sanitize_float(min_pos, 0.0, 0.0, float(led_count - 1))
        max_pos = DataSanitizer.sanitize_float(max_pos, float(led_count - 1), 0.0, float(led_count - 1))
        
        if min_pos > max_pos:
            min_pos, max_pos = max_pos, min_pos
        
        return [min_pos, max_pos]
    
    @staticmethod
    def sanitize_led_count(led_count: int, max_override: int = None) -> int:
        """Sanitize LED count với flexible approach"""
        default_range = ValidationUtils.get_default_led_count_range()
        
        if max_override is not None:
            return DataSanitizer.sanitize_int(led_count, 225, default_range[0], max_override)
        
        return DataSanitizer.sanitize_int(led_count, 225, default_range[0], default_range[1])
    
    @staticmethod
    def sanitize_speed_percent(speed_percent: int) -> int:
        """Sanitize speed percentage (0-1023%)"""
        speed_range = ValidationUtils.get_speed_range()
        return DataSanitizer.sanitize_int(speed_percent, 100, speed_range[0], speed_range[1])
    
    @staticmethod
    def sanitize_master_brightness(brightness: int) -> int:
        """Sanitize master brightness (0-255)"""
        brightness_range = ValidationUtils.get_brightness_range()
        return DataSanitizer.sanitize_int(brightness, 255, brightness_range[0], brightness_range[1])

def log_validation_error(error_msg: str, field_name: str = None):
    """Log validation error using the existing logger system"""
    logger = setup_logger("Validation")
    if field_name:
        logger.error(f"Validation Error in {field_name}: {error_msg}")
    else:
        logger.error(f"Validation Error: {error_msg}") 