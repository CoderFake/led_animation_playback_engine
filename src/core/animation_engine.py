"""
LED Animation Playback Engine with Dual Pattern Dissolve Support
Animation continues during crossfade transitions between patterns
"""

import asyncio
import time
import threading
import json
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from collections import deque
from pathlib import Path

from .scene_manager import SceneManager
from .led_output import LEDOutput
from .osc_handler import OSCHandler
from config.settings import EngineSettings
from src.utils.logger import ComponentLogger
from src.utils.performance import PerformanceMonitor, ProfilerManager
from src.utils.fps_balancer import FPSBalancer
from src.utils.logging import AnimationLogger, OSCLogger, LoggingUtils
from src.utils.color_utils import ColorUtils
from src.models.common import EngineStats

logger = ComponentLogger("AnimationEngine")


class AnimationEngine:
    """
    Main animation engine with dual pattern dissolve support
    Manages continuous animation during pattern transitions
    """
    
    def __init__(self):
        self.scene_manager = SceneManager()
        self.led_output = LEDOutput()
        self.osc_handler = OSCHandler(self)
        
        self.stats = EngineStats()
        self.performance_monitor = PerformanceMonitor()
        self.profiler = ProfilerManager()
        self.fps_balancer = FPSBalancer(self)
        
        self.running = False
        self.animation_thread = None
        self.monitoring_thread = None
        
        self.target_fps = EngineSettings.ANIMATION.target_fps
        self.frame_interval = 1.0 / self.target_fps
        
        self.sleep_overhead_history = deque(maxlen=30)
        self.average_sleep_overhead = 0.0
        
        self.master_brightness = EngineSettings.ANIMATION.master_brightness
        self.speed_percent = 100
        
        self.engine_start_time = 0.0
        self.frame_count = 0
        self.last_frame_time = 0.0
        
        self.fps_history = deque(maxlen=60)
        self.fps_calculation_time = 0.0
        self.fps_frame_count = 0
        
        self.state_callbacks: List[Callable] = []
        self._lock = threading.RLock()
        
        self.animation_running = False
        self.animation_should_stop = False
        
        self.stats.total_leds = EngineSettings.ANIMATION.led_count
        self.stats.target_fps = self.target_fps
        self.stats.master_brightness = self.master_brightness
        self.stats.speed_percent = self.speed_percent
        self.stats.animation_running = False
        
        self._setup_osc_handlers()
        
        self.fps_balancer.add_callback(self._on_fps_event)
        self.fps_balancer.set_desired_fps(self.target_fps)
       
    def get_current_led_count(self) -> int:
        """Get current LED count from active scene"""
        try:
            scene_info = self.scene_manager.get_scene_info()
            return scene_info.get('led_count', EngineSettings.ANIMATION.led_count)
        except Exception:
            return EngineSettings.ANIMATION.led_count
    
    def _setup_osc_handlers(self):
        """Setup OSC message handlers for dual pattern dissolve system"""
        handlers = {
            "/load_json": self.handle_load_json,
            "/change_scene": self.handle_change_scene,
            "/change_effect": self.handle_change_effect,
            "/change_palette": self.handle_change_palette,
            "/load_dissolve_json": self.handle_load_dissolve_json,
            "/set_dissolve_pattern": self.handle_set_dissolve_pattern,
            "/set_speed_percent": self.handle_set_speed_percent,
            "/master_brightness": self.handle_master_brightness,
        }
        
        for address, handler in handlers.items():
            self.osc_handler.add_handler(address, handler)
        
        self.osc_handler.add_palette_handler(self.handle_palette_color)
    
    async def start(self):
        """Start animation engine with dual pattern dissolve support"""
        try:
            logger.info("Starting Animation Engine...")
            
            self.engine_start_time = time.time()
            self.frame_count = 0
            self.last_frame_time = self.engine_start_time
            self.fps_calculation_time = self.engine_start_time
            self.fps_frame_count = 0

            await self.scene_manager.initialize()
            await self.led_output.start()
            await self.osc_handler.start()
            self._start_monitoring()
            self.fps_balancer.start()
            
            self.running = True
            
            logger.info("Animation Engine started successfully")
            
        except Exception as e:
            logger.error(f"Error starting engine: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise
    
    def _start_animation_loop(self):
        """Start animation loop with dual pattern support"""
        if self.animation_running:
            logger.warning("Animation loop already running")
            return
        
        if self.animation_thread and self.animation_thread.is_alive():
            logger.warning("Animation thread already exists")
            return
        
        self.animation_running = True
        self.animation_should_stop = False
        
        with self._lock:
            self.stats.animation_running = True
        
        self.animation_thread = threading.Thread(
            target=self._animation_loop,
            daemon=True,
            name="DualPatternAnimationLoop"
        )
        self.animation_thread.start()
       
        if not self.animation_thread.is_alive():
            logger.error("Animation thread failed to start!")
            self.animation_running = False
            with self._lock:
                self.stats.animation_running = False
    
    def _stop_animation_loop(self):
        """Stop animation loop"""
        if not self.animation_running:
            return
        
        logger.info("Stopping dual pattern animation loop...")
        
        self.animation_should_stop = True
        
        if self.animation_thread and self.animation_thread.is_alive():
            self.animation_thread.join(timeout=2.0)
            if self.animation_thread.is_alive():
                logger.warning("Animation thread did not stop gracefully")
        
        self.animation_running = False
        with self._lock:
            self.stats.animation_running = False
        
        logger.info("Dual pattern animation loop stopped")
    
    def _check_scenes_available(self) -> bool:
        """Check if scenes are available for animation"""
        try:
            scene_info = self.scene_manager.get_scene_info()
            return scene_info.get('scene_id') is not None
        except Exception:
            return False
    
    async def stop(self):
        """Stop animation engine"""
        logger.info("Stopping Animation Engine...")
        
        self.running = False
        
        self._stop_animation_loop()
        
        logger.info("Stopping FPS Balancer...")
        self.fps_balancer.stop()
        
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            logger.info("Stopping monitoring thread...")
            self.monitoring_thread.join(timeout=1.0)
            
        await self.osc_handler.stop()
        await self.led_output.stop()
        
        final_stats = self.get_stats()
        logger.info(f"Engine stopped after {final_stats.animation_time:.1f}s")
        logger.info(f"Processed {final_stats.frame_count} frames")
        if final_stats.frame_count > 0:
            logger.info(f"Average FPS: {final_stats.actual_fps:.1f}")
        
        logger.info("Animation Engine stopped successfully")
    
    def _start_monitoring(self):
        """Start performance monitoring thread"""
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            return
            
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True,
            name="PerformanceMonitor"
        )
        self.monitoring_thread.start()
    
    def _animation_loop(self):
        """
        Main animation loop with dual pattern support
        Continues animation during dissolve transitions
        """
        try:
            self.last_frame_time = time.time()
            self.fps_calculation_time = self.last_frame_time
            self.fps_frame_count = 0
            
            fps_log_interval = 600
            
            while self.running and not self.animation_should_stop:
                if not self._check_scenes_available():
                    logger.debug("No scenes available, pausing animation loop")
                    time.sleep(0.1)
                    continue
                
                frame_start = time.perf_counter()
                
                try:
                    frame_timeout = 0.1
                    
                    delta_time = frame_start - self.last_frame_time
                    self.last_frame_time = frame_start
                    
                    frame_process_start = time.perf_counter()
                    self._update_frame_with_dual_patterns(delta_time, frame_start)
                    
                    frame_process_time = time.perf_counter() - frame_process_start
                    if frame_process_time > frame_timeout:
                        logger.warning(f"Frame processing took {frame_process_time*1000:.1f}ms (timeout: {frame_timeout*1000:.1f}ms)")
                    
                    with self._lock:
                        self.frame_count += 1
                        self.stats.frame_count = self.frame_count
                        self.stats.animation_time = frame_start - self.engine_start_time
                        self.stats.total_leds = self.get_current_led_count()
                    
                    self.performance_monitor.record_frame(frame_start)
                    self.fps_frame_count += 1
                    
                    if delta_time > 0:
                        instant_fps = 1.0 / delta_time
                        self.fps_history.append(instant_fps)
                        
                        self.fps_balancer.update_led_count(self.get_current_led_count())
                    
                    if self.fps_frame_count >= fps_log_interval:
                        self._log_fps_status()
                        self.fps_frame_count = 0
                    
                except Exception as e:
                    logger.error(f"Error in animation loop frame: {e}")
                    import traceback
                    logger.error(f"Traceback: {traceback.format_exc()}")
                
                frame_time = time.perf_counter() - frame_start
                sleep_time = max(0, self.frame_interval - frame_time)
                
                if frame_time > self.frame_interval * 2.0:
                    logger.warning(f"Frame processing exceeded target by {(frame_time - self.frame_interval)*1000:.1f}ms")
                
                target_frame_end = frame_start + self.frame_interval
                while time.perf_counter() < target_frame_end:
                    pass
                
                actual_loop_time = time.perf_counter() - frame_start
                actual_sleep_time = actual_loop_time - frame_time
                
                self.fps_balancer.update_timing(frame_time, actual_sleep_time, actual_loop_time)
            
            logger.info("Dual pattern animation loop stopped")
        
        except Exception as e:
            logger.error(f"FATAL ERROR in dual pattern animation loop: {e}")
            import traceback
            logger.error(f"Animation loop traceback: {traceback.format_exc()}")
        finally:
            self.animation_running = False
            with self._lock:
                self.stats.animation_running = False
    
    def _monitoring_loop(self):
        """Performance monitoring loop"""
        
        while self.running:
            try:
                time.sleep(60)
                
                if not self.running:
                    break
                
                perf_stats = self.performance_monitor.get_stats()
                
                if self.animation_running and perf_stats['current_fps'] < self.target_fps * 0.8:
                    logger.warning(f"Performance degraded: {perf_stats['current_fps']:.1f} FPS")
                
                if perf_stats['frame_time_max_ms'] > self.frame_interval * 1000 * 2:
                    logger.warning(f"High frame time detected: {perf_stats['frame_time_max_ms']:.1f}ms")
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
        
        logger.debug("Performance monitoring loop stopped")
    
    def _on_fps_event(self, event_data):
        """Handle FPS balancer events"""
        try:
            event_type = event_data.get("type")
            
            if event_type == "target_fps_adjusted":
                self._handle_target_fps_adjusted(event_data)
            elif event_type == "led_count_changed":
                self._handle_led_count_changed(event_data)
                
        except Exception as e:
            logger.error(f"Error in FPS event callback: {e}")
    
    def _handle_target_fps_adjusted(self, event_data):
        """Handle target FPS adjustment"""
        new_target = event_data.get("new_target", 0)
        
        with self._lock:
            self.target_fps = new_target
            self.frame_interval = 1.0 / self.target_fps
            self.stats.target_fps = new_target
    
    def _handle_led_count_changed(self, event_data):
        """Handle LED count change"""
        old_count = event_data.get("old_count", 0)
        new_count = event_data.get("new_count", 0)
        ratio = event_data.get("ratio", 1.0)
        
        self.fps_history.clear()
    
    def _log_fps_status(self):
        """Log FPS status with dual pattern information"""
        if self.fps_history:
            average_fps = sum(self.fps_history) / len(self.fps_history)
            
            with self._lock:
                self.stats.actual_fps = average_fps
                
                if self.animation_running:
                    led_colors = self.scene_manager.get_rendered_led_array()
                    led_colors = ColorUtils.apply_colors_to_array(led_colors, self.master_brightness)
                    
                    active_leds = ColorUtils.count_active_leds(led_colors)
                    self.stats.active_leds = active_leds
                else:
                    self.stats.active_leds = 0
            
            efficiency = (average_fps / self.target_fps) * 100
            
            logger.info(f"Frame: {self.frame_count}, FPS: {average_fps:.1f}, Speed: {self.speed_percent}%, Active: {self.stats.active_leds} LEDs")
            
            if efficiency < 90:
                logger.warning(f"Performance below target: {efficiency:.1f}%")
    
    def get_stats(self) -> EngineStats:
        """Get engine statistics with dual pattern information"""
        with self._lock:
            stats_copy = EngineStats()
            stats_copy.target_fps = self.target_fps
            stats_copy.actual_fps = self.stats.actual_fps
            stats_copy.frame_count = self.frame_count
            stats_copy.animation_running = self.animation_running
            
            if self.animation_running:
                led_colors = self.scene_manager.get_rendered_led_array()
                led_colors = ColorUtils.apply_colors_to_array(led_colors, self.master_brightness)
                
                active_leds = ColorUtils.count_active_leds(led_colors)
                stats_copy.active_leds = active_leds
            else:
                stats_copy.active_leds = 0
                
            stats_copy.total_leds = self.get_current_led_count()
            stats_copy.animation_time = time.time() - self.engine_start_time
            stats_copy.master_brightness = self.master_brightness
            stats_copy.speed_percent = self.speed_percent
            
            self.stats.active_leds = stats_copy.active_leds
            self.stats.total_leds = stats_copy.total_leds
            
            return stats_copy
    
    def reset_fps_balancer(self):
        """Reset FPS balancer"""
        try:
            self.fps_balancer.force_reset()
            logger.info("FPS balancer reset to default state")
        except Exception as e:
            logger.error(f"Error resetting FPS balancer: {e}")
            raise
    
    def _update_frame_with_dual_patterns(self, delta_time: float, current_time: float):
        """
        Update frame with dual pattern support during dissolve transitions
        Both old and new patterns continue animating during crossfade
        """
        try:
            with self._lock:
                speed_percent = self.speed_percent
                master_brightness = self.master_brightness
            
            adjusted_delta = delta_time * (speed_percent / 100.0)
            
            self.scene_manager.update_animation(adjusted_delta)
            
            led_colors = self.scene_manager.get_rendered_led_array()
            led_colors = ColorUtils.apply_colors_to_array(led_colors, master_brightness)
            
            self.led_output.send_led_data(led_colors)
                
        except Exception as e:
            LoggingUtils.log_error("Animation", f"Error in _update_frame_with_dual_patterns: {e}")
            import traceback
            LoggingUtils.log_error("Animation", f"Traceback: {traceback.format_exc()}")
    
    def add_state_callback(self, callback: Callable):
        """Add state change callback"""
        self.state_callbacks.append(callback)
    
    def _notify_state_change(self):
        """Notify state change callbacks"""
        for callback in self.state_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"Error in state callback: {e}")
    
    def get_scene_info(self) -> Dict[str, Any]:
        """Get scene information"""
        return self.scene_manager.get_scene_info()
    
    def set_target_fps(self, target_fps: float, propagate_to_balancer: bool = True):
        """Set target FPS"""
        try:
            if target_fps <= 0 or target_fps > 240:
                raise ValueError(f"Target FPS must be between 1 and 240, got {target_fps}")
            
            with self._lock:
                old_fps = self.target_fps
                self.target_fps = target_fps
                self.frame_interval = 1.0 / self.target_fps
                self.stats.target_fps = target_fps
                self.fps_history.clear()
                if propagate_to_balancer:
                    self.fps_balancer.set_desired_fps(target_fps)
                
        except Exception as e:
            logger.error(f"Error setting target FPS: {e}")
            raise
    
    def get_led_colors(self) -> List[List[int]]:
        """Get current LED colors with dual pattern support"""
        if not self.animation_running:
            return [[0, 0, 0] for _ in range(self.get_current_led_count())]
            
        led_colors = self.scene_manager.get_rendered_led_array()
        led_colors = ColorUtils.apply_colors_to_array(led_colors, self.master_brightness)
        
        return led_colors
    
    # ==================== OSC Handlers ====================
    
    def handle_load_json(self, address: str, *args):
        """Handle loading JSON scenes for dual pattern system"""
        try:
            OSCLogger.log_received(address, list(args))
            
            if not args or len(args) == 0:
                OSCLogger.log_validation_failed(address, "file_path", None, "non-empty string")
                return
            
            file_path = str(args[0])
            
            if not file_path.lower().endswith('.json'):
                file_path += '.json'
                LoggingUtils.log_info("Animation", f"Appended .json extension: {file_path}")
            
            LoggingUtils.log_info("Animation", f"Loading JSON from: {file_path}")
            
            success = False
            error_message = None
            
            try:
                file_path_obj = Path(file_path)
                if not file_path_obj.exists():
                    error_message = f"File not found: {file_path}"
                    LoggingUtils.log_error("Animation", error_message)
                    OSCLogger.log_error(address, error_message)
                    return
                
                success = self.scene_manager.load_multiple_scenes_from_file(file_path)
                
                if success:
                    if self.animation_running:
                        self._stop_animation_loop()
                        LoggingUtils.log_info("Animation", "Stopped animation loop for new JSON data")
                    
                    scenes_count = len(self.scene_manager.scenes) if hasattr(self.scene_manager, 'scenes') else None
                    LoggingUtils.log_info("Animation", f"Successfully loaded {scenes_count} scenes from {file_path}")
                    AnimationLogger.log_json_loaded("scenes", scenes_count)
                    
                    LoggingUtils.log_info("Animation", "New scenes loaded. Waiting for scene switch to start animation.")
                    
                    self._notify_state_change()
                    OSCLogger.log_processed(address, "success")
                else:
                    error_message = f"Failed to load or parse JSON file: {file_path}"
                    LoggingUtils.log_error("Animation", error_message)
                    OSCLogger.log_error(address, error_message)
                        
            except Exception as load_error:
                error_message = f"Error loading JSON scenes: {load_error}"
                LoggingUtils.log_error("Animation", error_message)
                OSCLogger.log_error(address, error_message)
                
        except Exception as e:
            error_message = f"Error in handle_load_json: {e}"
            LoggingUtils.log_error("Animation", error_message)
            OSCLogger.log_error(address, error_message)
    
    def handle_change_scene(self, address: str, *args):
        """Handle scene change with dual pattern dissolve"""
        try:
            OSCLogger.log_received(address, list(args))
            
            if not args or len(args) == 0:
                OSCLogger.log_validation_failed(address, "scene_id", None, "integer")
                return
            
            try:
                scene_id = int(args[0])
                LoggingUtils.log_info("Animation", f"Attempting to change to scene: {scene_id}")
                
                available_scenes = self.scene_manager.get_available_scenes()
                if not available_scenes:
                    error_message = "No scenes are loaded"
                    LoggingUtils.log_error("Animation", error_message)
                    OSCLogger.log_error(address, error_message)
                    return
                
                if scene_id not in available_scenes:
                    error_message = f"Scene {scene_id} not found. Available scenes: {available_scenes}"
                    LoggingUtils.log_warning("Animation", error_message)
                    OSCLogger.log_validation_failed(address, "scene_id", scene_id, f"one of {available_scenes}")
                    return
                
                success = self.scene_manager.change_scene(scene_id)
                
                if success:
                    LoggingUtils.log_info("Animation", f"Successfully changed to scene {scene_id}")
                    AnimationLogger.log_scene_change(scene_id)
                    
                    if not self.animation_running:
                        self._start_animation_loop()
                        LoggingUtils.log_info("Animation", "Animation loop started after scene switch")
                    
                    self._notify_state_change()
                    OSCLogger.log_processed(address, "success")
                else:
                    error_message = f"Failed to change to scene {scene_id}"
                    LoggingUtils.log_error("Animation", error_message)
                    OSCLogger.log_error(address, error_message)
                    
            except ValueError:
                OSCLogger.log_validation_failed(address, "scene_id", args[0], "integer")
                
        except Exception as e:
            error_message = f"Error in handle_change_scene: {e}"
            LoggingUtils.log_error("Animation", error_message)
            OSCLogger.log_error(address, error_message)
    
    def handle_change_effect(self, address: str, *args):
        """Handle effect change with dual pattern dissolve"""
        try:
            OSCLogger.log_received(address, list(args))
            
            if not args or len(args) == 0:
                OSCLogger.log_validation_failed(address, "effect_id", None, "integer")
                return
            
            try:
                effect_id = int(args[0])
                LoggingUtils.log_info("Animation", f"Changing effect to: {effect_id}")
            
                scene_info = self.scene_manager.get_scene_info()
                if not scene_info or scene_info.get('scene_id') is None:
                    error_message = "No active scene for effect change"
                    LoggingUtils.log_warning("Animation", error_message)
                    OSCLogger.log_error(address, error_message)
                    return
                
                available_effects = scene_info.get('available_effects', [])
                if effect_id < 0 or effect_id not in available_effects:
                    error_message = f"Effect {effect_id} not found. Available effects: {available_effects}"
                    LoggingUtils.log_warning("Animation", error_message)
                    OSCLogger.log_validation_failed(address, "effect_id", effect_id, f"one of {available_effects}")
                    return
                
                success = self.scene_manager.change_effect(effect_id)
                
                if success:
                    LoggingUtils.log_info("Animation", f"Successfully changed effect to {effect_id}")
                    AnimationLogger.log_effect_change(effect_id)
                    self._notify_state_change()
                    OSCLogger.log_processed(address, "success")
                else:
                    error_message = f"Failed to change effect to {effect_id}"
                    LoggingUtils.log_error("Animation", error_message)
                    OSCLogger.log_error(address, error_message)
                    
            except ValueError:
                OSCLogger.log_validation_failed(address, "effect_id", args[0], "integer")
                
        except Exception as e:
            error_message = f"Error in handle_change_effect: {e}"
            LoggingUtils.log_error("Animation", error_message)
            OSCLogger.log_error(address, error_message)

    def handle_change_palette(self, address: str, *args):
        """Handle palette change with dual pattern dissolve"""
        try:
            OSCLogger.log_received(address, list(args))
            
            if not args or len(args) == 0:
                OSCLogger.log_validation_failed(address, "palette_id", None, "integer")
                return
            
            try:
                palette_id = int(args[0])
                LoggingUtils.log_info("Animation", f"Changing palette to: {palette_id}")
            
                scene_info = self.scene_manager.get_scene_info()
                if not scene_info or scene_info.get('scene_id') is None:
                    error_message = "No active scene for palette change"
                    LoggingUtils.log_warning("Animation", error_message)
                    OSCLogger.log_error(address, error_message)
                    return
                
                available_palettes = scene_info.get('available_palettes', [])
                if available_palettes and palette_id not in available_palettes:
                    error_message = f"Palette {palette_id} not found. Available palettes: {available_palettes}"
                    LoggingUtils.log_warning("Animation", error_message)
                    OSCLogger.log_validation_failed(address, "palette_id", palette_id, f"one of {available_palettes}")
                    return
                
                success = self.scene_manager.change_palette(palette_id)
                
                if success:
                    LoggingUtils.log_info("Animation", f"Successfully changed palette to {palette_id}")
                    AnimationLogger.log_palette_change(palette_id)
                    self._notify_state_change()
                    OSCLogger.log_processed(address, "success")
                else:
                    error_message = f"Failed to change palette to {palette_id}"
                    LoggingUtils.log_error("Animation", error_message)
                    OSCLogger.log_error(address, error_message)
                    
            except ValueError:
                OSCLogger.log_validation_failed(address, "palette_id", args[0], "integer")
                
        except Exception as e:
            error_message = f"Error in handle_change_palette: {e}"
            LoggingUtils.log_error("Animation", error_message)
            OSCLogger.log_error(address, error_message)
    
    def handle_palette_color(self, address: str, palette_id: int, color_id: int, rgb: List[int]):
        """Handle palette color update"""
        try:
            LoggingUtils.log_info("Animation", f"Updating palette {palette_id} color {color_id} to RGB({rgb[0]},{rgb[1]},{rgb[2]})")
            
            if palette_id < 0 or palette_id > 4:
                LoggingUtils.log_warning("Animation", f"Invalid palette ID {palette_id} (must be 0-4)")
                return
            
            if color_id < 0 or color_id > 5:
                LoggingUtils.log_warning("Animation", f"Invalid color ID {color_id} (must be 0-5)")
                return
            
            if len(rgb) != 3:
                LoggingUtils.log_warning("Animation", f"Invalid RGB values: {rgb} (must have 3 values)")
                return
            
            validated_rgb = []
            for i, value in enumerate(rgb):
                if not isinstance(value, int) or value < 0 or value > 255:
                    LoggingUtils.log_warning("Animation", f"Invalid RGB[{i}] = {value} (must be 0-255)")
                    return
                validated_rgb.append(value)
            
            success = self.scene_manager.update_palette_color(palette_id, color_id, validated_rgb[0], validated_rgb[1], validated_rgb[2])
            
            if success:
                LoggingUtils.log_info("Animation", f"Successfully updated palette {palette_id}[{color_id}] = RGB({validated_rgb[0]},{validated_rgb[1]},{validated_rgb[2]})")
                self._notify_state_change()
            else:
                LoggingUtils.log_warning("Animation", f"Failed to update palette {palette_id} color {color_id}")
                
        except Exception as e:
            LoggingUtils.log_error("Animation", f"Error in handle_palette_color: {e}")
    
    def handle_load_dissolve_json(self, address: str, *args):
        """Handle loading dissolve patterns"""
        try:
            OSCLogger.log_received(address, list(args))
            
            if not args or len(args) == 0:
                OSCLogger.log_validation_failed(address, "file_path", None, "non-empty string")
                return
            
            file_path = str(args[0])
            LoggingUtils.log_info("Animation", f"Loading dissolve patterns from: {file_path}")
            
            if not file_path.lower().endswith('.json'):
                file_path += '.json'
                LoggingUtils.log_info("Animation", f"Appended .json extension: {file_path}")
            
            success = self.scene_manager.load_dissolve_json(file_path)
            
            if success:
                LoggingUtils.log_info("Animation", f"Successfully loaded dissolve patterns from {file_path}")
                AnimationLogger.log_json_loaded("dissolve")
                self._notify_state_change()
                OSCLogger.log_processed(address, "success")
            else:
                error_message = f"Failed to load dissolve patterns from {file_path}"
                LoggingUtils.log_error("Animation", error_message)
                OSCLogger.log_error(address, error_message)
                
        except Exception as e:
            error_message = f"Error in handle_load_dissolve_json: {e}"
            LoggingUtils.log_error("Animation", error_message)
            OSCLogger.log_error(address, error_message)
    
    def handle_set_dissolve_pattern(self, address: str, *args):
        """Handle setting dissolve pattern"""
        try:
            OSCLogger.log_received(address, list(args))
            
            if not args or len(args) == 0:
                OSCLogger.log_validation_failed(address, "pattern_id", None, "integer")
                return
            
            try:
                pattern_id = int(args[0])
                LoggingUtils.log_info("Animation", f"Setting dissolve pattern to: {pattern_id}")
                
                success = self.scene_manager.set_dissolve_pattern(pattern_id)
                
                if success:
                    LoggingUtils.log_info("Animation", f"Successfully set dissolve pattern to {pattern_id}")
                    self._notify_state_change()
                    OSCLogger.log_processed(address, "success")
                else:
                    available = self.scene_manager.dissolve_patterns.get_available_patterns()
                    error_message = f"Pattern {pattern_id} not found. Available: {available}"
                    LoggingUtils.log_warning("Animation", error_message)
                    OSCLogger.log_validation_failed(address, "pattern_id", pattern_id, f"one of {available}")
                    
            except ValueError:
                OSCLogger.log_validation_failed(address, "pattern_id", args[0], "integer")
                
        except Exception as e:
            error_message = f"Error in handle_set_dissolve_pattern: {e}"
            LoggingUtils.log_error("Animation", error_message)
            OSCLogger.log_error(address, error_message)
    
    def handle_set_speed_percent(self, address: str, *args):
        """Handle speed change with proper scene manager integration"""
        try:
            OSCLogger.log_received(address, list(args))
            
            if not args or len(args) == 0:
                OSCLogger.log_validation_failed(address, "speed_percent", None, "integer")
                return
            
            try:
                speed_percent = int(args[0])
                
                if speed_percent < 0:
                    LoggingUtils.log_warning("Animation", f"Invalid speed percent {speed_percent} (must be >= 0)")
                    speed_percent = 0
                
                if speed_percent > 1023:
                    LoggingUtils.log_warning("Animation", f"Invalid speed percent {speed_percent} (must be <= 1023)")
                    speed_percent = 1023
                
                with self._lock:
                    old_speed = self.speed_percent
                    self.speed_percent = speed_percent
                    self.stats.speed_percent = speed_percent
                    
                    self.scene_manager.set_speed_percent(speed_percent)
                    
                    self._notify_state_change()
                
                LoggingUtils.log_info("Animation", f"Successfully set animation speed from {old_speed}% to {self.speed_percent}%")
                OSCLogger.log_processed(address, "success")
                
            except ValueError:
                OSCLogger.log_validation_failed(address, "speed_percent", args[0], "integer")
                
        except Exception as e:
            error_message = f"Error in handle_set_speed_percent: {e}"
            LoggingUtils.log_error("Animation", error_message)
            OSCLogger.log_error(address, error_message)
    
    def handle_master_brightness(self, address: str, *args):
        """Handle master brightness change"""
        try:
            OSCLogger.log_received(address, list(args))
            
            if not args or len(args) == 0:
                OSCLogger.log_validation_failed(address, "brightness", None, "integer")
                return
            
            try:
                brightness = int(args[0])
                
                if brightness < 0:
                    LoggingUtils.log_warning("Animation", f"Invalid brightness {brightness} (must be >= 0)")
                    brightness = 0
                
                if brightness > 255:
                    LoggingUtils.log_warning("Animation", f"Invalid brightness {brightness} (must be <= 255)")
                    brightness = 255
                
                with self._lock:
                    old_brightness = self.master_brightness
                    self.master_brightness = brightness
                    self.stats.master_brightness = brightness
                    self._notify_state_change()
                
                LoggingUtils.log_info("Animation", f"Successfully set master brightness from {old_brightness} to {self.master_brightness}")
                OSCLogger.log_processed(address, "success")
                
            except ValueError:
                OSCLogger.log_validation_failed(address, "brightness", args[0], "integer")
                
        except Exception as e:
            error_message = f"Error in handle_master_brightness: {e}"
            LoggingUtils.log_error("Animation", error_message)
            OSCLogger.log_error(address, error_message)