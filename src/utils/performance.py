"""
Performance monitoring utilities
"""

import time
import threading
from typing import Dict, Any
from collections import deque


class PerformanceMonitor:
    """
    Monitor performance of engine
    """
    
    def __init__(self, max_samples: int = 1000):
        self.max_samples = max_samples
        self.frame_times = deque(maxlen=max_samples)
        self.fps_history = deque(maxlen=60)
        
        self.start_time = time.time()
        self.last_frame_time = 0.0
        self.frame_count = 0
        
        self._lock = threading.Lock()
    
    def record_frame(self, frame_time: float):
        """
        Record time for a frame
        """
        with self._lock:
            current_time = time.time()
            
            if self.last_frame_time > 0:
                delta = current_time - self.last_frame_time
                self.frame_times.append(delta)
                
                if delta > 0:
                    fps = 1.0 / delta
                    self.fps_history.append(fps)
            
            self.last_frame_time = current_time
            self.frame_count += 1
    
    def get_average_fps(self) -> float:
        """
        Get average FPS
        """
        with self._lock:
            if not self.fps_history:
                return 0.0
            return sum(self.fps_history) / len(self.fps_history)
    
    def get_current_fps(self) -> float:
        """
        Get current FPS
        """
        with self._lock:
            if not self.fps_history:
                return 0.0
            return self.fps_history[-1] if self.fps_history else 0.0
    
    def get_frame_time_stats(self) -> Dict[str, float]:
        """
        Get frame time statistics
        """
        with self._lock:
            if not self.frame_times:
                return {
                    "avg": 0.0,
                    "min": 0.0,
                    "max": 0.0,
                    "std": 0.0
                }
            
            frame_times_list = list(self.frame_times)
            avg = sum(frame_times_list) / len(frame_times_list)
            min_time = min(frame_times_list)
            max_time = max(frame_times_list)
            
            variance = sum((t - avg) ** 2 for t in frame_times_list) / len(frame_times_list)
            std = variance ** 0.5
            
            return {
                "avg": avg * 1000,
                "min": min_time * 1000, 
                "max": max_time * 1000,
                "std": std * 1000
            }
    
    def get_uptime(self) -> float:
        """
        Get uptime
        """
        return time.time() - self.start_time
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get all statistics
        """
        frame_stats = self.get_frame_time_stats()
        
        return {
            "uptime": self.get_uptime(),
            "total_frames": self.frame_count,
            "current_fps": self.get_current_fps(),
            "average_fps": self.get_average_fps(),
            "frame_time_avg_ms": frame_stats["avg"],
            "frame_time_min_ms": frame_stats["min"],
            "frame_time_max_ms": frame_stats["max"],
            "frame_time_std_ms": frame_stats["std"]
        }
    
    def reset(self):
        """
        Reset all statistics
        """
        with self._lock:
            self.frame_times.clear()
            self.fps_history.clear()
            self.start_time = time.time()
            self.last_frame_time = 0.0
            self.frame_count = 0


class ProfileTimer:
    """
    Timer to profile functions
    """
    
    def __init__(self, name: str):
        self.name = name
        self.start_time = 0.0
        self.total_time = 0.0
        self.call_count = 0
    
    def __enter__(self):
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = time.perf_counter() - self.start_time
        self.total_time += elapsed
        self.call_count += 1
    
    def get_average_time(self) -> float:
        """
        Get average time per call
        """
        return self.total_time / self.call_count if self.call_count > 0 else 0.0
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics
        """
        return {
            "name": self.name,
            "total_time": self.total_time,
            "call_count": self.call_count,
            "average_time": self.get_average_time()
        }


class ProfilerManager:
    """
    Manage multiple profiler timers
    """
    
    def __init__(self):
        self.timers: Dict[str, ProfileTimer] = {}
        self._lock = threading.Lock()
    
    def get_timer(self, name: str) -> ProfileTimer:
        """
        Get or create timer
        """
        with self._lock:
            if name not in self.timers:
                self.timers[name] = ProfileTimer(name)
            return self.timers[name]
    
    def profile(self, name: str):
        """
        Decorator to profile function
        """
        def decorator(func):
            def wrapper(*args, **kwargs):
                with self.get_timer(name):
                    return func(*args, **kwargs)
            return wrapper
        return decorator
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        Get statistics for all timers
        """
        with self._lock:
            return {name: timer.get_stats() for name, timer in self.timers.items()}
    
    def reset_all(self):
        """
        Reset all timers
        """
        with self._lock:
            for timer in self.timers.values():
                timer.total_time = 0.0
                timer.call_count = 0