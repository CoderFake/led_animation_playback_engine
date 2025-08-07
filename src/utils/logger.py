"""
Logging system optimized for terminal and background operation
Provides structured logging with color support and performance optimization
"""

import logging
import sys
import os
from pathlib import Path
from typing import Optional
from logging.handlers import RotatingFileHandler
import colorama
from colorama import Fore, Back, Style
from datetime import datetime
from config.settings import EngineSettings

colorama.init(autoreset=True)


class LoggerMode:
    """
    Logger mode configuration for different execution environments
    """
    TERMINAL = "terminal"
    DAEMON = "daemon"
    
    _current_mode = TERMINAL
    
    @classmethod
    def set_mode(cls, mode: str):
        """Set logger mode"""
        cls._current_mode = mode
    
    @classmethod
    def get_mode(cls) -> str:
        """Get current mode"""
        return cls._current_mode
    
    @classmethod
    def is_terminal(cls) -> bool:
        """Check if terminal mode"""
        return cls._current_mode == cls.TERMINAL


class ColoredFormatter(logging.Formatter):
    """
    Enhanced formatter with color support for terminal output
    """
    
    COLORS = {
        'DEBUG': Fore.CYAN,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.RED + Back.WHITE + Style.BRIGHT
    }
    
    COMPONENT_COLORS = {
        'AnimationEngine': Fore.BLUE,
        'SceneManager': Fore.MAGENTA,
        'LEDOutput': Fore.YELLOW,
        'OSCHandler': Fore.CYAN,
        'PerformanceMonitor': Fore.WHITE,
    }
    
    def format(self, record):
        """Format log record with colors and structure"""
        if LoggerMode.is_terminal() and sys.stdout.isatty():
            level_color = self.COLORS.get(record.levelname, '')
            record.levelname = f"{level_color}{record.levelname:<8}{Style.RESET_ALL}"
            
            component = record.name.split('.')[-1]
            component_color = self.COMPONENT_COLORS.get(component, Fore.BLUE)
            record.name = f"{component_color}{component:<15}{Style.RESET_ALL}"
            
            if record.levelname.strip() in ['ERROR', 'CRITICAL']:
                record.msg = f"{Fore.RED}{record.msg}{Style.RESET_ALL}"
        
        return super().format(record)


class PerformanceLogHandler(logging.Handler):
    """
    High-performance log handler optimized for background operation
    """
    
    def __init__(self, stream=None):
        super().__init__()
        self.stream = stream or sys.stdout
        self.last_flush = datetime.now()
        self.buffer = []
        self.buffer_size = 100
        
    def emit(self, record):
        """Emit log record with buffering for performance"""
        try:
            msg = self.format(record)
            
            if LoggerMode.is_terminal():
                self.stream.write(msg + '\n')
                if record.levelno >= logging.WARNING:
                    self.stream.flush()
            else:
                self.buffer.append(msg)
                if len(self.buffer) >= self.buffer_size:
                    self._flush_buffer()
                    
        except Exception:
            self.handleError(record)
    
    def _flush_buffer(self):
        """Flush buffered messages"""
        if self.buffer:
            for msg in self.buffer:
                self.stream.write(msg + '\n')
            self.stream.flush()
            self.buffer.clear()
            self.last_flush = datetime.now()


class OSCLogger:
    """
    Specialized logger for OSC messages with immediate output
    Optimized for high-frequency message logging
    """
    
    def __init__(self):
        self.logger = setup_logger("OSC")
        self.message_count = 0
        self.error_count = 0
        self.last_message_time = 0
        
    def log_message(self, address: str, args: tuple):
        """Log OSC message with performance optimization"""
        self.message_count += 1
        
        if self.message_count % 100 == 0:
            args_str = ' '.join(str(arg) for arg in args[:3]) if args else ''
            if len(args) > 3:
                args_str += f" ... ({len(args)} args)"
            
        elif address.startswith('/palette/') or 'load' in address or 'change' in address:
            args_str = ' '.join(str(arg) for arg in args) if args else ''
            self.logger.info(f"OSC {address} {args_str}")
    
    def log_error(self, message: str):
        """Log OSC error with immediate output"""
        self.error_count += 1
        self.logger.error(f"OSC ERROR: {message}")
    
    def get_stats(self) -> dict:
        """Get OSC logging statistics"""
        return {
            "message_count": self.message_count,
            "error_count": self.error_count
        }


def setup_logger(name: str) -> logging.Logger:
    """
    Setup optimized logger for terminal and background operation
    """
    logger = logging.getLogger(name)
    
    if logger.handlers:
        return logger
    
    level = getattr(logging, EngineSettings.LOGGING.level.upper(), logging.INFO)
    logger.setLevel(level)
    
    if LoggerMode.is_terminal():
        console_handler = PerformanceLogHandler(sys.stdout)
        console_handler.setLevel(level)
        
        console_formatter = ColoredFormatter(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
    
    if EngineSettings.LOGGING.file_output:
        try:
            log_dir = Path(EngineSettings.LOGGING.log_directory)
            log_dir.mkdir(parents=True, exist_ok=True)
            
            log_file = log_dir / "led_engine.log"
            
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=50*1024*1024,
                backupCount=EngineSettings.LOGGING.max_log_files
            )
            file_handler.setLevel(level)
            
            file_formatter = logging.Formatter(
                '%(asctime)s [%(levelname)-8s] %(name)-20s: %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
            
        except Exception as e:
            print(f"Warning: Could not setup file logging: {e}", file=sys.stderr)
    
    logger.propagate = False
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get configured logger instance"""
    return setup_logger(name)


def set_terminal_mode():
    """Set logger to terminal mode"""
    LoggerMode.set_mode(LoggerMode.TERMINAL)


def set_daemon_mode():
    """Set logger to daemon mode"""
    LoggerMode.set_mode(LoggerMode.DAEMON)


class ComponentLogger:
    """
    Specialized logger for engine components with performance tracking
    """
    
    def __init__(self, component_name: str):
        self.logger = setup_logger(component_name)
        self.component_name = component_name
        self.start_time = datetime.now()
        self.operation_count = 0
        
    def info(self, message: str, *args, **kwargs):
        """Log info message"""
        self.logger.info(message, *args, **kwargs)
        
    def debug(self, message: str, *args, **kwargs):
        """Log debug message"""
        self.logger.debug(message, *args, **kwargs)
        
    def warning(self, message: str, *args, **kwargs):
        """Log warning message"""
        self.logger.warning(message, *args, **kwargs)
        
    def error(self, message: str, *args, **kwargs):
        """Log error message"""
        self.logger.error(message, *args, **kwargs)
        
    def critical(self, message: str, *args, **kwargs):
        """Log critical message"""
        self.logger.critical(message, *args, **kwargs)
        
    def operation(self, operation_name: str, details: str = ""):
        """Log operation with performance tracking"""
        self.operation_count += 1
        if details:
            self.logger.debug(f"{operation_name}: {details}")
        else:
            self.logger.debug(f"{operation_name} completed")
            
    def performance(self, metric_name: str, value: float, unit: str = ""):
        """Log performance metric"""
        self.logger.info(f"PERF {metric_name}: {value:.3f}{unit}")
        
    def get_stats(self) -> dict:
        """Get component logging statistics"""
        uptime = (datetime.now() - self.start_time).total_seconds()
        return {
            "component": self.component_name,
            "uptime_seconds": uptime,
            "operations": self.operation_count,
            "ops_per_second": self.operation_count / uptime if uptime > 0 else 0
        }


def setup_background_logging():
    """Setup logging optimized for background/daemon operation"""
    LoggerMode.set_mode(LoggerMode.DAEMON)
    
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    file_handler = RotatingFileHandler(
        "led_engine_daemon.log",
        maxBytes=100*1024*1024,
        backupCount=5
    )
    file_handler.setLevel(logging.INFO)
    
    file_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)-8s] %(name)-20s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    
    root_logger.addHandler(file_handler)
    root_logger.setLevel(logging.INFO)