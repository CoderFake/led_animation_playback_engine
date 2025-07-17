"""
FPS Balancer - Intelligent Timing Adjustment
Equation: processing_time + sleep_time = loop_time (1/fps)
"""

import time
import threading
from collections import deque
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass

from config.settings import EngineSettings
from .logging import LoggingUtils

logger = LoggingUtils._get_logger("FPSBalancer")


@dataclass
class TimingMetrics:
    processing_time: float
    sleep_time: float
    loop_time: float
    actual_fps: float
    target_fps: float
    desired_fps: float
    led_count: int


class FPSBalancer:
    
    def __init__(self, animation_engine=None, led_output=None):
        self.animation_engine = animation_engine
        self.led_output = led_output
        self.config = EngineSettings.FPS_BALANCER
        
        self.desired_fps = EngineSettings.ANIMATION.target_fps
        
        self.processing_times = deque(maxlen=20)
        self.loop_times = deque(maxlen=20)
        
        self.current_metrics = TimingMetrics(
            processing_time=0.0,
            sleep_time=0.0,
            loop_time=0.0,
            actual_fps=0.0,
            target_fps=self.desired_fps,
            desired_fps=self.desired_fps,
            led_count=0
        )
        
        self.last_led_count = 0
        self.last_adjustment_time = 0.0
        
        self.running = False
        self.balancer_thread = None
        self._lock = threading.RLock()
        
        self.callbacks: List[Callable] = []
        

    def start(self):
        """Start FPS balancer""" 
        if not self.config.enabled:
            return
        
        self.running = True
    
    def stop(self):
        """Stop FPS balancer"""
        self.running = False
    
    def update_timing(self, processing_time: float, sleep_time: float, loop_time: float):
        """Update timing metrics from animation loop"""
        with self._lock:
            self.processing_times.append(processing_time)
            self.loop_times.append(loop_time)
            
            self.current_metrics.processing_time = processing_time
            self.current_metrics.sleep_time = sleep_time
            self.current_metrics.loop_time = loop_time
            self.current_metrics.actual_fps = 1.0 / loop_time if loop_time > 0 else 0.0
    
    def update_led_count(self, led_count: int):
        """Update LED count and trigger adjustment if needed"""
        with self._lock:
            if led_count != self.last_led_count:
                if self.last_led_count > 0:
                    self._adjust_for_led_count_change(self.last_led_count, led_count)
                
                self.last_led_count = led_count
                self.current_metrics.led_count = led_count
    
    def set_desired_fps(self, desired_fps: float):
        """Set desired FPS (what user wants)"""
        with self._lock:
            self.desired_fps = desired_fps
            self.current_metrics.desired_fps = desired_fps
    
    def add_callback(self, callback: Callable):
        """Add callback when there is a change"""
        self.callbacks.append(callback)
    
    def _calculate_optimal_target_fps(self):
        """Calculate optimal target FPS to achieve desired FPS from settings"""
        with self._lock:
            if len(self.processing_times) < 2:
                return
            
            recent_processing = list(self.processing_times)[-3:]
            avg_processing_time = sum(recent_processing) / len(recent_processing)
            
            desired_loop_time = 1.0 / self.desired_fps
            
            if avg_processing_time >= desired_loop_time:
                optimal_target_fps = 1.0 / avg_processing_time
            else:
                optimal_target_fps = self.desired_fps
            
            optimal_target_fps = max(10, min(300, optimal_target_fps))
            
            current_target = self.current_metrics.target_fps
            if abs(optimal_target_fps - current_target) > 0.5:
                self.current_metrics.target_fps = optimal_target_fps
                
                self._notify_callbacks({
                    "type": "target_fps_adjusted",
                    "old_target": current_target,
                    "new_target": optimal_target_fps,
                    "desired_fps": self.desired_fps,
                    "processing_time": avg_processing_time
                })
    
    def _adjust_for_led_count_change(self, old_count: int, new_count: int):
        """Adjust when LED count changes"""
        try:
            ratio = new_count / old_count if old_count > 0 else 1.0
            
            if ratio > 1.2 or ratio < 0.8:  
                self.processing_times.clear()
                self.sleep_overheads.clear()
                self.loop_times.clear()
                
                self._notify_callbacks({
                    "type": "led_count_changed",
                    "old_count": old_count,
                    "new_count": new_count,
                    "ratio": ratio
                })
            
        except Exception as e:
            logger.error(f"Error adjusting for LED count change: {e}")
    
    def _notify_callbacks(self, event_data: Dict[str, Any]):
        """Notify callbacks"""
        for callback in self.callbacks:
            try:
                callback(event_data)
            except Exception as e:
                logger.error(f"Error in callback: {e}")