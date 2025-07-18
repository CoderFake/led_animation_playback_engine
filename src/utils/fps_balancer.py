
"""
Complete FPS Balancer Implementation
Auto-adjust target FPS to ensure stable output and prevent LED lag/jitter
"""

import time
import threading
from collections import deque
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass

from config.settings import EngineSettings
from src.models.common import FPSAdjustment
from src.utils.logging import LoggingUtils


logger = LoggingUtils._get_logger("FPSBalancer")

class FPSBalancer:
    """
    Complete FPS Balancer with real adaptive logic
    Auto-adjust target FPS to maintain stable output
    """
    
    def __init__(self, animation_engine=None):
        self.animation_engine = animation_engine
        self.config = EngineSettings.FPS_BALANCER
        
        self.desired_fps = EngineSettings.ANIMATION.target_fps
        self.current_target_fps = self.desired_fps
        
        self.processing_times = deque(maxlen=20)
        self.loop_times = deque(maxlen=20)
        self.led_count_history = deque(maxlen=10)
        
        self.min_fps = max(1, self.desired_fps * 0.3)  
        self.max_fps = min(240, self.desired_fps * 1.2)  
        self.adjustment_threshold = 0.85 

        self.last_adjustment_time = 0.0
        self.adjustment_cooldown = 2.0 
        self.stable_frames = 0
        self.min_stable_frames = 30 
        
        self.running = False
        self._lock = threading.RLock()
        self.callbacks: List[Callable[[Dict[str, Any]], None]] = []
        
    def start(self):
        """Start FPS balancer"""
        if not self.config.enabled:
            return
        
        self.running = True
    
    def add_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Add a callback for FPS events"""
        with self._lock:
            if callback not in self.callbacks:
                self.callbacks.append(callback)

    def stop(self):
        """Stop FPS balancer"""
        self.running = False
    
    def update_timing(self, processing_time: float, sleep_time: float, loop_time: float):
        """Update timing metrics from animation loop"""
        with self._lock:
            self.processing_times.append(processing_time)
            self.loop_times.append(loop_time)
            
            if len(self.processing_times) >= 5:
                self._evaluate_fps_adjustment()
    
    def update_led_count(self, led_count: int):
        """Update LED count and trigger evaluation if significant change"""
        with self._lock:
            self.led_count_history.append(led_count)
            
            if len(self.led_count_history) >= 2:
                old_count = self.led_count_history[-2]
                change_ratio = led_count / max(1, old_count)
                
                if change_ratio > 1.5 or change_ratio < 0.7: 
                    self._clear_history()
                    self._evaluate_fps_adjustment()
    
    def set_desired_fps(self, desired_fps: float):
        """Set desired FPS and recalculate limits"""
        with self._lock:
            old_desired = self.desired_fps
            self.desired_fps = max(1, min(240, desired_fps))
            self.min_fps = max(1, self.desired_fps * 0.3)
            self.max_fps = min(240, self.desired_fps * 1.2)

            if abs(self.current_target_fps - old_desired) < 5:
                self._adjust_target_fps(self.desired_fps, "desired_fps_changed")
            
    def _evaluate_fps_adjustment(self):
        """Evaluate if FPS adjustment is needed"""
        if not self.running or not self.processing_times:
            return
        
        current_time = time.time()
        if current_time - self.last_adjustment_time < self.adjustment_cooldown:
            return
        
        avg_processing = sum(list(self.processing_times)[-5:]) / min(5, len(self.processing_times))
        target_loop_time = 1.0 / self.current_target_fps
        efficiency = min(1.0, target_loop_time / max(0.001, avg_processing))
        
        led_count = self.led_count_history[-1] if self.led_count_history else 225
        
        if efficiency < self.adjustment_threshold:
            new_target = max(self.min_fps, 1.0 / avg_processing * 0.9) 
            new_target = min(new_target, self.current_target_fps * 0.8) 
            
            if new_target < self.current_target_fps - 1:
                self._adjust_target_fps(new_target, f"performance_low (efficiency={efficiency:.2f})")
                self.stable_frames = 0
        
        elif efficiency > 0.95 and self.current_target_fps < self.desired_fps:
            self.stable_frames += 1
            
            if self.stable_frames >= self.min_stable_frames:
                headroom = target_loop_time - avg_processing
                if headroom > target_loop_time * 0.2: 
                    new_target = min(self.desired_fps, self.current_target_fps * 1.1) 
                    
                    if new_target > self.current_target_fps + 1: 
                        self._adjust_target_fps(new_target, f"performance_good (efficiency={efficiency:.2f})")
                        self.stable_frames = 0
    
    def _adjust_target_fps(self, new_target: float, reason: str):
        """Actually adjust the target FPS"""
        with self._lock:
            old_target = self.current_target_fps
            self.current_target_fps = max(self.min_fps, min(self.max_fps, new_target))
            self.last_adjustment_time = time.time()
            
            if self.animation_engine and hasattr(self.animation_engine, 'set_target_fps'):
                self.animation_engine.set_target_fps(self.current_target_fps, propagate_to_balancer=False)
            
            led_count = self.led_count_history[-1] if self.led_count_history else 0
            avg_processing = sum(list(self.processing_times)[-3:]) / min(3, len(self.processing_times)) if self.processing_times else 0.0
            
            adjustment = FPSAdjustment(
                old_target=old_target,
                new_target=self.current_target_fps,
                reason=reason,
                led_count=led_count,
                avg_processing_time=avg_processing * 1000
            )
            
            self._notify_adjustment(adjustment)
            self._clear_history()

    def _notify_adjustment(self, adj: FPSAdjustment):
        """Notify listeners about the FPS adjustment"""
        with self._lock:
            event_data = {
                "type": "target_fps_adjusted",
                "old_target": adj.old_target,
                "new_target": adj.new_target,
                "reason": adj.reason,
                "led_count": adj.led_count,
                "avg_processing_time": adj.avg_processing_time
            }
            for callback in self.callbacks:
                try:
                    callback(event_data)
                except Exception as e:
                    logger.error(f"Error in FPS balancer callback: {e}")
    
    def _clear_history(self):
        """Clear performance history after adjustment"""
        self.processing_times.clear()
        self.loop_times.clear()
        self.stable_frames = 0
   