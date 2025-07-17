"""
Centralized logging utilities for LED Animation Engine
Eliminates duplicate logging code and provides consistent logging format
"""

import time
from typing import Any, Dict, Optional
from enum import Enum
from .logger import setup_logger

class LogLevel(Enum):
    """Log levels for different types of messages"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    PERFORMANCE = "PERFORMANCE"
    OSC = "OSC"
    VALIDATION = "VALIDATION"

class LoggingUtils:
    """Centralized logging utilities"""
    
    @staticmethod
    def _get_logger(component: str):
        """Get logger for component"""
        return setup_logger(component)
    
    @staticmethod
    def log_info(component: str, message: str, extra_data: Dict = None):
        """Log info message"""
        logger = LoggingUtils._get_logger(component)
        if extra_data:
            extra_str = ", ".join(f"{k}={v}" for k, v in extra_data.items())
            message += f" ({extra_str})"
        logger.info(message)
    
    @staticmethod
    def log_error(component: str, message: str, extra_data: Dict = None):
        """Log error message"""
        logger = LoggingUtils._get_logger(component)
        if extra_data:
            extra_str = ", ".join(f"{k}={v}" for k, v in extra_data.items())
            message += f" ({extra_str})"
        logger.error(message)
    
    @staticmethod
    def log_warning(component: str, message: str, extra_data: Dict = None):
        """Log warning message"""
        logger = LoggingUtils._get_logger(component)
        if extra_data:
            extra_str = ", ".join(f"{k}={v}" for k, v in extra_data.items())
            message += f" ({extra_str})"
        logger.warning(message)
    
    @staticmethod
    def log_debug(component: str, message: str, extra_data: Dict = None):
        """Log debug message"""
        logger = LoggingUtils._get_logger(component)
        if extra_data:
            extra_str = ", ".join(f"{k}={v}" for k, v in extra_data.items())
            message += f" ({extra_str})"
        logger.debug(message)
    
    @staticmethod
    def log_performance(component: str, operation: str, duration_ms: float, 
                       extra_data: Dict = None):
        """Log performance timing"""
        logger = LoggingUtils._get_logger(component)
        perf_data = {"duration_ms": f"{duration_ms:.2f}"}
        if extra_data:
            perf_data.update(extra_data)
        
        extra_str = ", ".join(f"{k}={v}" for k, v in perf_data.items())
        logger.info(f"PERFORMANCE: {operation} completed ({extra_str})")
    
    @staticmethod
    def log_validation_error(component: str, field_name: str, error_msg: str, 
                           value: Any = None):
        """Log validation error with field context"""
        logger = LoggingUtils._get_logger(component)
        extra_data = {"field": field_name}
        if value is not None:
            extra_data["value"] = str(value)
        
        extra_str = ", ".join(f"{k}={v}" for k, v in extra_data.items())
        logger.error(f"VALIDATION: {error_msg} ({extra_str})")

class OSCLogger:
    """Specialized logging for OSC operations"""
    
    @staticmethod
    def _get_logger():
        """Get OSC logger"""
        return setup_logger("OSC")
    
    @staticmethod
    def log_received(address: str, args: list, extra_data: Dict = None):
        """Log OSC message received"""
        logger = OSCLogger._get_logger()
        message = f"Received OSC: {address}"
        if args:
            message += f" with args: {args}"
        if extra_data:
            extra_str = ", ".join(f"{k}={v}" for k, v in extra_data.items())
            message += f" ({extra_str})"
        logger.info(message)
    
    @staticmethod
    def log_processed(address: str, result: str, duration_ms: float = None):
        """Log OSC message processed"""
        logger = OSCLogger._get_logger()
        message = f"Processed {address} (result={result}"
        if duration_ms is not None:
            message += f", duration_ms={duration_ms:.2f}"
        message += ")"
        logger.info(message)
    
    @staticmethod
    def log_error(address: str, error_msg: str, args: list = None):
        """Log OSC processing error"""
        logger = OSCLogger._get_logger()
        message = f"Processing failed: {error_msg} (address={address}"
        if args:
            message += f", args={args}"
        message += ")"
        logger.error(message)
    
    @staticmethod
    def log_validation_failed(address: str, field_name: str, value: Any, 
                            expected: str = None):
        """Log OSC validation failure"""
        logger = OSCLogger._get_logger()
        message = f"Validation failed for {address} (field={field_name}, value={value}"
        if expected:
            message += f", expected={expected}"
        message += ")"
        logger.error(message)

class AnimationLogger:
    """Specialized logging for animation operations"""
    
    @staticmethod
    def _get_logger():
        """Get Animation logger"""
        return setup_logger("Animation")
    
    @staticmethod
    def log_scene_change(scene_id: int, effect_id: int = None, palette_id: int = None):
        """Log scene change operation"""
        logger = AnimationLogger._get_logger()
        message = f"Scene changed (scene_id={scene_id}"
        if effect_id is not None:
            message += f", effect_id={effect_id}"
        if palette_id is not None:
            message += f", palette_id={palette_id}"
        message += ")"
        logger.info(message)
    
    @staticmethod
    def log_effect_change(effect_id: int, scene_id: int = None):
        """Log effect change operation"""
        logger = AnimationLogger._get_logger()
        message = f"Effect changed (effect_id={effect_id}"
        if scene_id is not None:
            message += f", scene_id={scene_id}"
        message += ")"
        logger.info(message)
    
    @staticmethod
    def log_palette_change(palette_id: int, scene_id: int = None):
        """Log palette change operation"""
        logger = AnimationLogger._get_logger()
        message = f"Palette changed (palette_id={palette_id}"
        if scene_id is not None:
            message += f", scene_id={scene_id}"
        message += ")"
        logger.info(message)
    
    @staticmethod
    def log_dissolve_started(pattern_id: int, scene_id: int = None):
        """Log dissolve transition started"""
        logger = AnimationLogger._get_logger()
        message = f"Dissolve transition started (pattern_id={pattern_id}"
        if scene_id is not None:
            message += f", scene_id={scene_id}"
        message += ")"
        logger.info(message)
    
    @staticmethod
    def log_json_loaded(json_type: str, scenes_count: int = None, 
                       patterns_count: int = None):
        """Log JSON data loaded"""
        logger = AnimationLogger._get_logger()
        message = f"JSON data loaded (type={json_type}"
        if scenes_count is not None:
            message += f", scenes_count={scenes_count}"
        if patterns_count is not None:
            message += f", patterns_count={patterns_count}"
        message += ")"
        logger.info(message)
    
    @staticmethod
    def log_parameter_change(param_name: str, value: Any, scene_id: int = None):
        """Log parameter change"""
        logger = AnimationLogger._get_logger()
        if scene_id is not None:
            message += f", scene_id={scene_id}"
        message += ")"
        logger.info(message)
    
    @staticmethod
    def log_validation_error(operation: str, error_msg: str, 
                           scene_id: int = None, segment_id: int = None):
        """Log animation validation error"""
        logger = AnimationLogger._get_logger()
        message = f"Validation failed: {error_msg} (operation={operation}"
        if scene_id is not None:
            message += f", scene_id={scene_id}"
        if segment_id is not None:
            message += f", segment_id={segment_id}"
        message += ")"
        logger.error(message)

class PerformanceTracker:
    """Performance tracking utilities"""
    
    def __init__(self, component: str, operation: str):
        self.component = component
        self.operation = operation
        self.start_time = None
        self.extra_data = {}
        self.logger = setup_logger(component)
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration_ms = (time.time() - self.start_time) * 1000
            message = f"PERFORMANCE: {self.operation} completed (duration_ms={duration_ms:.2f}"
            if self.extra_data:
                extra_str = ", ".join(f"{k}={v}" for k, v in self.extra_data.items())
                message += f", {extra_str}"
            message += ")"
            self.logger.info(message)
    
    def add_data(self, key: str, value: Any):
        """Add extra data to performance log"""
        self.extra_data[key] = str(value)

def track_performance(component: str, operation: str):
    """Decorator for performance tracking"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            with PerformanceTracker(component, operation):
                return func(*args, **kwargs)
        return wrapper
    return decorator

def log_osc_received(address: str, args: list = None):
    """Quick log for OSC message received"""
    OSCLogger.log_received(address, args or [])

def log_osc_processed(address: str, result: str = "success"):
    """Quick log for OSC message processed"""
    OSCLogger.log_processed(address, result)

def log_osc_error(address: str, error: str, args: list = None):
    """Quick log for OSC error"""
    OSCLogger.log_error(address, error, args)

def log_scene_change(scene_id: int, effect_id: int = None, palette_id: int = None):
    """Quick log for scene change"""
    AnimationLogger.log_scene_change(scene_id, effect_id, palette_id)

def log_json_loaded(json_type: str, count: int = None):
    """Quick log for JSON loaded"""
    if json_type == "scenes":
        AnimationLogger.log_json_loaded(json_type, scenes_count=count)
    elif json_type == "dissolve":
        AnimationLogger.log_json_loaded(json_type, patterns_count=count)
    else:
        AnimationLogger.log_json_loaded(json_type) 