"""
Engine settings configuration for zero-origin IDs and expanded features
Provides comprehensive configuration for all engine components
"""

import json
import os
from pathlib import Path
from typing import List
from pydantic import BaseModel, Field, validator


class OSCConfig(BaseModel):
    """
    OSC protocol configuration for input and output
    """
    input_host: str = Field(default="127.0.0.1", description="OSC input host address")
    input_port: int = Field(default=8000, description="OSC input port", ge=1024, le=65535)
    output_address: str = Field(default="/light/serial", description="OSC output address for LED data")
    buffer_size: int = Field(default=8192, description="OSC buffer size in bytes")
    timeout: float = Field(default=1.0, description="OSC message timeout in seconds")
    
    @validator('input_host')
    def validate_host(cls, v):
        """Validate host address format"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Host address cannot be empty")
        return v.strip()


class LEDDestination(BaseModel):
    """
    LED output destination configuration for multi-device support
    """
    ip: str = Field(description="Target IP address")
    port: int = Field(description="Target port", ge=1024, le=65535)
    start_led: int = Field(default=0, description="Start LED index for range mode", ge=0)
    end_led: int = Field(default=-1, description="End LED index for range mode (-1 means full range)")
    copy_mode: bool = Field(default=True, description="True=full copy, False=range mode")
    enabled: bool = Field(default=True, description="Enable this destination")
    name: str = Field(default="", description="Human-readable name for this destination")
    
    @validator('name', pre=True, always=True)
    def set_default_name(cls, v, values):
        """Set default name if not provided"""
        if not v and 'ip' in values:
            return f"Device_{values['ip']}"
        return v


class AnimationConfig(BaseModel):
    """
    Animation engine configuration 
    """
    target_fps: int = Field(default=60, description="Target animation FPS", ge=1, le=240)
    led_count: int = Field(default=225, description="Default LED count (dynamic per scene)", ge=1, le=10000000)
    master_brightness: int = Field(default=255, description="Master brightness level", ge=0, le=255)
    
    max_segment_length: int = Field(default=10000, description="Maximum segment length for safety", ge=1, le=100000)
    dissolve_batch_size: int = Field(default=1000, description="Batch size for large dissolve operations", ge=100, le=10000)
    boundary_check_enabled: bool = Field(default=True, description="Enable boundary checking for safety")
    
    led_destinations: List[LEDDestination] = Field(
        default_factory=lambda: [
            LEDDestination(
                ip="127.0.0.1", 
                port=7000, 
                start_led=0, 
                end_led=204, 
                copy_mode=False, 
                enabled=True, 
                name="Ceiling_Strip"
            ),
            LEDDestination(
                ip="127.0.0.1", 
                port=7001, 
                start_led=205,
                end_led=409, 
                copy_mode=False, 
                enabled=True, 
                name="Floor_Strip"
            )
        ],
        description="LED output destinations matching simulator configuration"
    )
    
    performance_mode: str = Field(default="balanced", description="Performance mode: high, balanced, or efficient")
    max_frame_time_ms: float = Field(default=50.0, description="Maximum allowed frame processing time")
    
    speed_range_max: int = Field(default=1023, description="Maximum speed percentage")
    fractional_positioning: bool = Field(default=True, description="Enable fractional positioning with fade effects")
    time_based_dimmer: bool = Field(default=True, description="Enable time-based dimmer instead of position-based")
    
    minimum_brightness: float = Field(default=0.02, description="Minimum brightness to ensure visibility")
    brightness_smoothing: bool = Field(default=True, description="Enable brightness smoothing")
    
    @validator('led_destinations')
    def validate_destinations(cls, v):
        """Validate LED serial output configuration"""
        if not v:
            raise ValueError("At least one LED serial output must be configured")
        
        for dest in v:
            if not hasattr(dest, 'ip') or not hasattr(dest, 'port'):
                raise ValueError("Each LED destination must have 'ip' and 'port' attributes")
            
            if not (1024 <= dest.port <= 65535):
                raise ValueError(f"Port {dest.port} must be between 1024 and 65535")
        
        return v


class DissolveConfig(BaseModel):
    """
    Dissolve transition system configuration
    """
    enabled: bool = Field(default=True, description="Enable dissolve transition system")
    default_pattern_id: int = Field(default=0, description="Default dissolve pattern ID (zero-origin)")
    patterns_file: str = Field(default="src/data/jsons/dissolve_pattern.json", description="Dissolve patterns JSON file")
    
    max_simultaneous_transitions: int = Field(default=10, description="Maximum simultaneous LED transitions")
    transition_precision_ms: int = Field(default=10, description="Transition timing precision in milliseconds")


class LoggingConfig(BaseModel):
    """
    Logging system configuration
    """
    level: str = Field(default="INFO", description="Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL")
    console_output: bool = Field(default=True, description="Enable console output")
    file_output: bool = Field(default=True, description="Enable file output")
    log_directory: str = Field(default="src/data/logs", description="Log file directory")
    max_log_files: int = Field(default=10, description="Maximum number of log files to keep", ge=1, le=100)
    max_file_size_mb: int = Field(default=50, description="Maximum log file size in MB", ge=1, le=1000)
    
    performance_logging: bool = Field(default=True, description="Enable performance metrics logging")
    osc_message_logging: bool = Field(default=True, description="Enable OSC message logging")
    detailed_errors: bool = Field(default=True, description="Include stack traces in error logs")
    
    id_system_logging: bool = Field(default=True, description="Log ID system conversions (old to new format)")
    timing_system_logging: bool = Field(default=False, description="Log detailed timing system operations")
    
    @validator('level')
    def validate_log_level(cls, v):
        """Validate log level"""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v.upper()


class FPSBalancerConfig(BaseModel):
    """
    FPS Balancer configuration for adaptive performance management
    """
    enabled: bool = Field(default=True, description="Enable FPS balancer")
    target_fps_tolerance: float = Field(default=0.95, description="FPS tolerance", ge=0.8, le=1.0)
    adjustment_interval: float = Field(default=1.0, description="Check interval in seconds", ge=0.5, le=5.0)


class PerformanceConfig(BaseModel):
    """
    Performance monitoring and optimization configuration
    """
    enable_monitoring: bool = Field(default=True, description="Enable performance monitoring")
    monitoring_interval: int = Field(default=60, description="Monitoring interval in seconds", ge=1, le=3600)
    
    fps_history_size: int = Field(default=60, description="FPS history buffer size", ge=10, le=1000)
    performance_alerts: bool = Field(default=True, description="Enable performance alerts")
    alert_threshold_fps: float = Field(default=50.0, description="FPS threshold for alerts")
    
    profiling_enabled: bool = Field(default=False, description="Enable detailed profiling")
    memory_monitoring: bool = Field(default=True, description="Enable memory usage monitoring")
    cpu_monitoring: bool = Field(default=True, description="Enable CPU usage monitoring")
    
    fractional_rendering_optimization: bool = Field(default=True, description="Optimize fractional position rendering")
    time_based_optimization: bool = Field(default=True, description="Optimize time-based calculations")


class BackgroundConfig(BaseModel):
    """
    Configuration for background/daemon operation
    """
    daemon_mode: bool = Field(default=False, description="Run as daemon process")
    pid_file: str = Field(default="/tmp/led_engine.pid", description="PID file path")
    status_interval: int = Field(default=30, description="Status logging interval in seconds", ge=1, le=3600)
    
    auto_restart: bool = Field(default=False, description="Auto-restart on crash")
    max_restart_attempts: int = Field(default=3, description="Maximum restart attempts", ge=1, le=10)
    restart_delay: int = Field(default=5, description="Delay between restart attempts in seconds", ge=1, le=60)
    
    graceful_shutdown_timeout: int = Field(default=10, description="Graceful shutdown timeout in seconds", ge=1, le=60)
    save_state_on_exit: bool = Field(default=True, description="Save engine state on exit")


class EngineSettings:
    """
    Main engine configuration container with zero-origin ID support
    Handles loading, validation, and access to all configuration sections
    """
    
    def __init__(self):
        """Initialize settings from file or defaults"""
        self.OSC = OSCConfig()
        self.ANIMATION = AnimationConfig()
        self.DISSOLVE = DissolveConfig()
        self.LOGGING = LoggingConfig()
        self.FPS_BALANCER = FPSBalancerConfig()
        self.PERFORMANCE = PerformanceConfig()
        self.BACKGROUND = BackgroundConfig()
        
        self.DATA_DIRECTORY = Path("src/data")
        self.LOGS_DIRECTORY = Path(self.LOGGING.log_directory)
        self.JSONS_DIRECTORY = Path("src/data/jsons")
        self.DEFAULT_SCENE_FILE = "src/data/jsons/multiple_scenes.json"

        self.ensure_directories()
    
    def ensure_directories(self):
        """Ensure required directories exist"""
        try:
            self.DATA_DIRECTORY.mkdir(parents=True, exist_ok=True)
            self.LOGS_DIRECTORY.mkdir(parents=True, exist_ok=True)
            self.JSONS_DIRECTORY.mkdir(parents=True, exist_ok=True)
            
        except Exception as e:
            print(f"Error creating directories: {e}")
    
    def get_led_destinations(self) -> List[LEDDestination]:
        """Get validated LED destinations"""
        return self.ANIMATION.led_destinations
    
    def get_current_led_count(self) -> int:
        """Get current LED count (can be overridden by scene)"""
        return self.ANIMATION.led_count
    
    def validate_configuration(self) -> bool:
        """Validate entire configuration"""
        try:
            if self.ANIMATION.target_fps <= 0:
                raise ValueError("target_fps must be positive")
            
            if self.ANIMATION.led_count <= 0:
                raise ValueError("led_count must be positive")
            
            if not (0 <= self.ANIMATION.master_brightness <= 255):
                raise ValueError("master_brightness must be 0-255")
            
            if not (0 <= self.ANIMATION.speed_range_max <= 1023):
                raise ValueError("speed_range_max must be 0-1023")
            
            destinations = self.get_led_destinations()
            if not destinations:
                raise ValueError("At least one LED destination must be configured")
            
            for dest in destinations:
                if not hasattr(dest, 'ip') or not dest.ip:
                    raise ValueError("LED destination missing IP address")
                if not hasattr(dest, 'port') or not (1024 <= dest.port <= 65535):
                    raise ValueError("LED destination invalid port")
            
            if not self.DATA_DIRECTORY.exists():
                raise ValueError(f"Data directory does not exist: {self.DATA_DIRECTORY}")
            
            return True
            
        except Exception as e:
            print(f"Configuration validation error: {e}")
            return False
   
EngineSettings = EngineSettings()