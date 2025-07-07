"""
Engine settings configuration optimized for terminal and background operation
Provides comprehensive configuration for all engine components
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
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


class AnimationConfig(BaseModel):
    """
    Animation engine configuration
    """
    target_fps: int = Field(default=60, description="Target animation FPS", ge=1, le=120)
    led_count: int = Field(default=225, description="Total number of LEDs", ge=1, le=10000)
    master_brightness: int = Field(default=0, description="Master brightness level", ge=0, le=255)
    default_dissolve_time: int = Field(default=1000, description="Default dissolve time in ms", ge=0)
    
    led_destinations: List[Dict[str, Any]] = Field(
        default=[
            {"ip": "192.168.11.105", "port": 7000, "enabled": True},
        ],
        description="LED output destinations"
    )
    
    performance_mode: str = Field(default="balanced", description="Performance mode: high, balanced, or efficient")
    max_frame_time_ms: float = Field(default=50.0, description="Maximum allowed frame processing time")
    
    @validator('led_destinations')
    def validate_destinations(cls, v):
        """Validate LED serial output configuration"""
        if not v:
            raise ValueError("At least one LED serial output must be configured")
        
        for dest in v:
            if 'ip' not in dest or 'port' not in dest:
                raise ValueError("Each LED serial output must have 'ip' and 'port'")
            
            if not (1024 <= dest['port'] <= 65535):
                raise ValueError(f"Port {dest['port']} must be between 1024 and 65535")
        
        return v


class PatternTransitionConfig(BaseModel):
    """
    Pattern transition configuration for smooth effect changes
    """
    enabled: bool = Field(default=True, description="Enable pattern transitions")
    default_fade_in_ms: int = Field(default=100, description="Default fade-in time", ge=0, le=5000)
    default_fade_out_ms: int = Field(default=100, description="Default fade-out time", ge=0, le=5000)
    default_waiting_ms: int = Field(default=50, description="Default waiting time", ge=0, le=1000)
    
    smooth_transitions: bool = Field(default=True, description="Use smooth interpolation")
    transition_curve: str = Field(default="linear", description="Transition curve: linear, ease_in, ease_out, ease_in_out")


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
    
    @validator('level')
    def validate_log_level(cls, v):
        """Validate log level"""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v.upper()


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
    Main engine configuration container
    Handles loading, validation, and access to all configuration sections
    """
    
    def __init__(self):
        """Initialize settings from file or defaults"""
        self.OSC = OSCConfig()
        self.ANIMATION = AnimationConfig()
        self.PATTERN_TRANSITION = PatternTransitionConfig()
        self.LOGGING = LoggingConfig()
        self.PERFORMANCE = PerformanceConfig()
        self.BACKGROUND = BackgroundConfig()
        
        self.DATA_DIRECTORY = Path("src/data")
        self.LOGS_DIRECTORY = Path(self.LOGGING.log_directory)

        self.ensure_directories()
    
    def ensure_directories(self):
        """Ensure required directories exist"""
        try:
            self.DATA_DIRECTORY.mkdir(parents=True, exist_ok=True)
            self.LOGS_DIRECTORY.mkdir(parents=True, exist_ok=True)
            
        except Exception as e:
            print(f"Error creating directories: {e}")

EngineSettings = EngineSettings()
