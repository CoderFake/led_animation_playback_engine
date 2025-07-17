"""
FPS Balancer - Adaptive Performance Management System
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
class FPSMetrics:
    current_fps: float
    target_fps: float
    led_count: int
    fps_efficiency: float


class FPSBalancer:
    
    def __init__(self, animation_engine=None, led_output=None):
        self.animation_engine = animation_engine
        self.led_output = led_output
        self.config = EngineSettings.FPS_BALANCER
        
        self.fps_history = deque(maxlen=30)
        self.last_adjustment_time = 0.0
        
        self.current_metrics = FPSMetrics(
            current_fps=0.0,
            target_fps=EngineSettings.ANIMATION.target_fps,
            led_count=0,
            fps_efficiency=0.0
        )
        
        self.last_led_count = 0
        
        self.running = False
        self.balancer_thread = None
        self._lock = threading.RLock()
        
        self.callbacks: List[Callable] = []
        

    
    def start(self):
        """Start FPS balancer""" 
        if not self.config.enabled:
            return
            
        if self.running:
            return
            
        self.running = True
        self.balancer_thread = threading.Thread(target=self._balancer_loop, daemon=True)
        self.balancer_thread.start()
    
    def stop(self):
        """Stop FPS balancer"""
        self.running = False
        if self.balancer_thread:
            self.balancer_thread.join(timeout=3.0)
    
    def update_fps(self, fps: float):
        """Update current FPS"""
        with self._lock:
            self.fps_history.append(fps)
            self.current_metrics.current_fps = fps
            
            if self.current_metrics.target_fps > 0:
                self.current_metrics.fps_efficiency = fps / self.current_metrics.target_fps
    
    def update_led_count(self, led_count: int):
        """Update LED count and automatically adjust if changed"""
        with self._lock:
            if led_count != self.last_led_count:
                if self.last_led_count > 0:
                    self._adjust_for_led_count_change(self.last_led_count, led_count)
                
                self.last_led_count = led_count
                self.current_metrics.led_count = led_count
    
    def set_target_fps(self, target_fps: float):
        """Set target FPS"""
        with self._lock:
            self.current_metrics.target_fps = target_fps
    
    def add_callback(self, callback: Callable):
        """Add callback when there is a change"""
        self.callbacks.append(callback)

    def _get_led_output_fps(self) -> float:
        """Get actual FPS from LED output"""
        if not self.led_output:
            return 0.0
        
        try:
            stats = self.led_output.get_stats()
            return stats.get('actual_send_fps', 0.0)
        except Exception as e:
            logger.error(f"Error getting LED output FPS: {e}")
            return 0.0
    
    def _balancer_loop(self):
        """Main balancer loop"""
        
        while self.running:
            try:
                time.sleep(self.config.adjustment_interval)
                
                if not self.running:
                    break
                
                # Lấy FPS thực tế từ LED output
                led_fps = self._get_led_output_fps()
                if led_fps > 0:
                    self.update_fps(led_fps)
                if len(self.fps_history) == 0:
                    continue
                
                avg_fps = sum(self.fps_history) / len(self.fps_history)
                target_fps = self.current_metrics.target_fps
                
                if target_fps <= 0:
                    continue
                
                fps_ratio = avg_fps / target_fps
                
                if fps_ratio < self.config.target_fps_tolerance:
                    self._handle_low_fps(fps_ratio)
                elif fps_ratio > 1.1:
                    self._handle_high_fps(fps_ratio)
                
            except Exception as e:
                logger.error(f"Error in balancer loop: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
    
    def _adjust_for_led_count_change(self, old_count: int, new_count: int):
        """Adjust when LED count changes"""
        try:
            ratio = new_count / old_count if old_count > 0 else 1.0
            
            if ratio > 1.5:  
                self._notify_callbacks({"type": "led_increase", "ratio": ratio})
                
            elif ratio < 0.7:
                self._notify_callbacks({"type": "led_decrease", "ratio": ratio})
            
            self.fps_history.clear()
            
        except Exception as e:
            logger.error(f"Error adjusting for LED count change: {e}")
    
    def _handle_low_fps(self, fps_ratio: float):
        """Handle low FPS"""
        current_time = time.time()
        
        if current_time - self.last_adjustment_time < self.config.adjustment_interval:
            return
        
        self.last_adjustment_time = current_time
        
        deficit = (1.0 - fps_ratio) * 100
        
        self._notify_callbacks({
            "type": "fps_low", 
            "fps_ratio": fps_ratio,
            "deficit": deficit,
            "led_fps": self._get_led_output_fps()
        })
    
    def _handle_high_fps(self, fps_ratio: float):
        """Handle high FPS"""
        surplus = (fps_ratio - 1.0) * 100
        
        self._notify_callbacks({
            "type": "fps_high",
            "fps_ratio": fps_ratio,
            "surplus": surplus,
            "led_fps": self._get_led_output_fps()
        })
    
    def _notify_callbacks(self, event_data: Dict[str, Any]):
        """Notify callbacks"""
        for callback in self.callbacks:
            try:
                callback(event_data)
            except Exception as e:
                logger.error(f"Error in callback: {e}")
    
    def _log_status(self):
        pass
    
    def get_status_dict(self) -> Dict[str, Any]:
        """Get status dictionary for API"""
        with self._lock:
            avg_fps = sum(self.fps_history) / len(self.fps_history) if self.fps_history else 0.0
            
            return {
                "enabled": self.config.enabled,
                "target_fps": self.current_metrics.target_fps,
                "current_fps": self.current_metrics.current_fps,
                "average_fps": avg_fps,
                "led_count": self.current_metrics.led_count,
                "fps_efficiency": self.current_metrics.fps_efficiency,
                "tolerance": self.config.target_fps_tolerance,
                "adjustment_interval": self.config.adjustment_interval,
                "led_output_fps": self._get_led_output_fps()
            }
    
    def force_reset(self):
        """Force reset FPS balancer"""
        with self._lock:
            self.fps_history.clear()
            self.last_adjustment_time = 0.0
            self.last_led_count = 0
            
            self._notify_callbacks({"type": "reset"}) 