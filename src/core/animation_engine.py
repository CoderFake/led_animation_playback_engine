"""
LED Animation Playback Engine - Terminal Optimized
High-performance animation engine designed for background operation
"""

import asyncio
import time
import threading
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from collections import deque

from .scene_manager import SceneManager
from .led_output import LEDOutput
from .osc_handler import OSCHandler
from config.settings import EngineSettings
from src.utils.logger import ComponentLogger
from src.utils.performance import PerformanceMonitor, ProfilerManager

logger = ComponentLogger("AnimationEngine")


@dataclass
class EngineStats:
    """
    Comprehensive engine statistics for monitoring and debugging
    """
    target_fps: int = 60
    actual_fps: float = 0.0
    frame_count: int = 0
    active_leds: int = 0
    total_leds: int = 225
    animation_time: float = 0.0
    master_brightness: int = 255
    speed_percent: int = 100
    dissolve_time: int = 1000
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0


class AnimationEngine:
    """
    The main LED Animation Playback Engine optimized for terminal/background operation
    Handles real-time animation processing, OSC communication, and LED output
    """
    
    def __init__(self):
        self.scene_manager = SceneManager()
        self.led_output = LEDOutput()
        self.osc_handler = OSCHandler(self)
        
        self.stats = EngineStats()
        self.performance_monitor = PerformanceMonitor()
        self.profiler = ProfilerManager()
        
        self.running = False
        self.animation_thread = None
        self.monitoring_thread = None
        
        self.target_fps = EngineSettings.ANIMATION.target_fps
        self.frame_interval = 1.0 / self.target_fps
        
        self.master_brightness = EngineSettings.ANIMATION.master_brightness
        self.speed_percent = 100
        self.dissolve_time = EngineSettings.ANIMATION.default_dissolve_time
        
        self.engine_start_time = 0.0
        self.frame_count = 0
        self.last_frame_time = 0.0
        
        self.fps_history = deque(maxlen=60)
        self.fps_calculation_time = 0.0
        self.fps_frame_count = 0
        
        self.state_callbacks: List[Callable] = []
        self._lock = threading.RLock()
        
        self.stats.total_leds = EngineSettings.ANIMATION.led_count
        self.stats.target_fps = self.target_fps
        self.stats.master_brightness = self.master_brightness
        self.stats.speed_percent = self.speed_percent
        self.stats.dissolve_time = self.dissolve_time
        
        self._setup_osc_handlers()
        
        logger.info(f"AnimationEngine initialized")
        logger.info(f"Target: {self.target_fps} FPS, {self.stats.total_leds} LEDs")
        logger.info(f"Frame interval: {self.frame_interval*1000:.2f}ms")
    
    def _setup_osc_handlers(self):
        """
        Configure OSC message handlers for engine control
        """
        handlers = {
            "/load_json": self.handle_load_json,
            "/change_scene": self.handle_change_scene,
            "/change_effect": self.handle_change_effect,
            "/change_palette": self.handle_change_palette,
            "/set_dissolve_time": self.handle_set_dissolve_time,
            "/set_speed_percent": self.handle_set_speed_percent,
            "/master_brightness": self.handle_master_brightness,
            "/pattern_transition": self.handle_pattern_transition_config,
        }
        
        for address, handler in handlers.items():
            self.osc_handler.add_handler(address, handler)
        
        self.osc_handler.add_palette_handler(self.handle_palette_color)
        
        logger.info(f"Registered {len(handlers)} OSC handlers")
    
    async def start(self):
        """
        Start the animation engine and all subsystems
        """
        try:
            logger.info("Starting Animation Engine subsystems...")
            
            self.engine_start_time = time.time()
            self.frame_count = 0
            self.last_frame_time = self.engine_start_time
            self.fps_calculation_time = self.engine_start_time
            self.fps_frame_count = 0
            
            logger.info("Initializing Scene Manager...")
            await self.scene_manager.initialize()
            
            logger.info("Starting LED Output...")
            await self.led_output.start()
            
            logger.info("Starting OSC Handler...")
            await self.osc_handler.start()
            
            logger.info("Starting Animation Loop...")
            self._start_animation_loop()
            
            logger.info("Starting Performance Monitoring...")
            self._start_monitoring()
            
            self.running = True
            
            await asyncio.sleep(0.1)
            
            logger.info("Animation Engine started successfully")
            
        except Exception as e:
            logger.error(f"Error starting engine: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

    async def stop(self):
        """
        Stop the animation engine and cleanup resources
        """
        logger.info("Stopping Animation Engine...")
        
        self.running = False
        
        if self.animation_thread and self.animation_thread.is_alive():
            logger.info("Waiting for animation thread to stop...")
            self.animation_thread.join(timeout=2.0)
            if self.animation_thread.is_alive():
                logger.warning("Animation thread did not stop gracefully")
        
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            logger.info("Stopping monitoring thread...")
            self.monitoring_thread.join(timeout=1.0)
            
        await self.osc_handler.stop()
        await self.led_output.stop()
        
        final_stats = self.get_stats()
        logger.info(f"Engine stopped after {final_stats.animation_time:.1f}s")
        logger.info(f"Processed {final_stats.frame_count} frames")
        logger.info(f"Average FPS: {final_stats.actual_fps:.1f}")
        
        logger.info("Animation Engine stopped successfully")
    
    def _start_animation_loop(self):
        """
        Start the high-priority animation loop in a separate thread
        """
        if self.animation_thread and self.animation_thread.is_alive():
            return
            
        self.animation_thread = threading.Thread(
            target=self._animation_loop,
            daemon=True,
            name="AnimationLoop"
        )
        self.animation_thread.start()
        logger.info("Animation loop thread started")
    
    def _start_monitoring(self):
        """
        Start performance monitoring in a separate thread
        """
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            return
            
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True,
            name="PerformanceMonitor"
        )
        self.monitoring_thread.start()
        logger.info("Performance monitoring thread started")
    
    def _animation_loop(self):
        """
        Main high-performance animation loop
        Optimized for consistent timing and minimal latency
        """
        logger.info(f"Animation loop started - Target: {self.target_fps} FPS")
        
        self.last_frame_time = time.time()
        self.fps_calculation_time = self.last_frame_time
        self.fps_frame_count = 0
        
        fps_log_interval = 600
        performance_log_interval = 3600
        
        while self.running:
            frame_start = time.perf_counter()
            
            try:
                with self.profiler.get_timer("frame_processing"):
                    delta_time = frame_start - self.last_frame_time
                    self.last_frame_time = frame_start
                    
                    self._update_frame(delta_time)
                
                with self._lock:
                    self.frame_count += 1
                    self.stats.frame_count = self.frame_count
                    self.stats.animation_time = frame_start - self.engine_start_time
                
                self.performance_monitor.record_frame(frame_start)
                self.fps_frame_count += 1
                
                if delta_time > 0:
                    instant_fps = 1.0 / delta_time
                    self.fps_history.append(instant_fps)
                
                if self.fps_frame_count >= fps_log_interval:
                    self._log_fps_status()
                    self.fps_frame_count = 0
                
                if self.frame_count % performance_log_interval == 0 and self.frame_count > 0:
                    self._log_detailed_performance()
                
            except Exception as e:
                logger.error(f"Error in animation loop: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
            
            frame_time = time.perf_counter() - frame_start
            sleep_time = max(0, self.frame_interval - frame_time)
            
            if frame_time > self.frame_interval * 2.0:
                logger.warning(f"Frame processing exceeded target by {(frame_time - self.frame_interval)*1000:.1f}ms")
            
            if sleep_time > 0:
                time.sleep(sleep_time)
    
    def _monitoring_loop(self):
        """
        Background performance monitoring loop
        """
        logger.debug("Performance monitoring loop started")
        
        while self.running:
            try:
                time.sleep(60)
                
                if not self.running:
                    break
                
                perf_stats = self.performance_monitor.get_stats()
                
                if perf_stats['current_fps'] < self.target_fps * 0.8:
                    logger.warning(f"Performance degraded: {perf_stats['current_fps']:.1f} FPS")
                
                if perf_stats['frame_time_max_ms'] > self.frame_interval * 1000 * 2:
                    logger.warning(f"High frame time detected: {perf_stats['frame_time_max_ms']:.1f}ms")
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
        
        logger.debug("Performance monitoring loop stopped")
    
    def _log_fps_status(self):
        """
        Log FPS status and performance metrics
        """
        if self.fps_history:
            average_fps = sum(self.fps_history) / len(self.fps_history)
            
            with self._lock:
                self.stats.actual_fps = average_fps
            
            efficiency = (average_fps / self.target_fps) * 100
            
            logger.info(f"Frame {self.frame_count}: FPS {average_fps:.1f} ({efficiency:.1f}%), Active LEDs {self.stats.active_leds}")
            
            if efficiency < 90:
                logger.warning(f"Performance below target: {efficiency:.1f}%")
    
    def _log_detailed_performance(self):
        """
        Log detailed performance analysis
        """
        try:
            perf_stats = self.performance_monitor.get_stats()
            profiler_stats = self.profiler.get_all_stats()
            
            logger.info("=== DETAILED PERFORMANCE ANALYSIS ===")
            logger.performance("average_fps", perf_stats['average_fps'], " FPS")
            logger.performance("frame_time_avg", perf_stats['frame_time_avg_ms'], "ms")
            logger.performance("frame_time_max", perf_stats['frame_time_max_ms'], "ms")
            logger.performance("uptime", perf_stats['uptime'], "s")
            
            for timer_name, timer_stats in profiler_stats.items():
                if timer_stats['call_count'] > 0:
                    logger.performance(f"{timer_name}_avg", timer_stats['average_time']*1000, "ms")
            
        except Exception as e:
            logger.error(f"Error logging detailed performance: {e}")
    
    def get_stats(self) -> EngineStats:
        """
        Get comprehensive engine statistics
        """
        with self._lock:
            stats_copy = EngineStats()
            stats_copy.target_fps = self.target_fps
            stats_copy.actual_fps = self.stats.actual_fps
            stats_copy.frame_count = self.frame_count
            
            led_colors = self.scene_manager.get_led_output()
            active_leds = sum(1 for color in led_colors if any(c > 0 for c in color[:3]))
            stats_copy.active_leds = active_leds
            stats_copy.total_leds = self.stats.total_leds
            
            stats_copy.animation_time = time.time() - self.engine_start_time
            stats_copy.master_brightness = self.master_brightness
            stats_copy.speed_percent = self.speed_percent
            stats_copy.dissolve_time = self.dissolve_time
            
            self.stats.active_leds = active_leds
            
            return stats_copy
    
    def _update_frame(self, delta_time: float):
        """
        Update one animation frame with performance optimization
        """
        try:
            with self._lock:
                speed_percent = self.speed_percent
                master_brightness = self.master_brightness
            
            adjusted_delta = delta_time * (speed_percent / 100.0)
            
            with self.profiler.get_timer("scene_update"):
                self.scene_manager.update_animation(adjusted_delta)
            
            with self.profiler.get_timer("led_calculation"):
                led_colors = self.scene_manager.get_led_output()
            
            if master_brightness < 255:
                with self.profiler.get_timer("brightness_adjustment"):
                    brightness_factor = master_brightness / 255.0
                    led_colors = [
                        [int(c * brightness_factor) for c in color]
                        for color in led_colors
                    ]
            
            with self.profiler.get_timer("led_output"):
                self.led_output.send_led_data(led_colors)
                
        except Exception as e:
            logger.error(f"Error in _update_frame: {e}")
    
    def add_state_callback(self, callback: Callable):
        """
        Add a callback for state changes
        """
        self.state_callbacks.append(callback)
    
    def _notify_state_change(self):
        """
        Notify registered callbacks of state changes
        """
        for callback in self.state_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"Error in state callback: {e}")
    
    def get_scene_info(self) -> Dict[str, Any]:
        """
        Get current scene information
        """
        return self.scene_manager.get_current_scene_info()
    
    def get_led_colors(self) -> List[List[int]]:
        """
        Get current LED colors for external access
        """
        led_colors = self.scene_manager.get_led_output()
        
        if self.master_brightness < 255:
            brightness_factor = self.master_brightness / 255.0
            led_colors = [
                [int(c * brightness_factor) for c in color]
                for color in led_colors
            ]
        
        return led_colors
    
    def handle_load_json(self, address: str, *args):
        """
        Handle OSC message to load a JSON scene file
        """
        try:
            if not args or len(args) == 0:
                logger.warning("Missing json path argument")
                return
            
            file_path = str(args[0])
            
            success = False
            
            try:
                with self._lock:
                    if "multiple" in file_path.lower() or "scenes" in file_path.lower():
                        success = self.scene_manager.load_multiple_scenes_from_file(file_path)
                    else:
                        success = self.scene_manager.load_scene_from_file(file_path)
                        
                    if not success:
                        success = self.scene_manager.load_multiple_scenes_from_file(file_path)
                        
                if success:
                    self._notify_state_change()
                    logger.operation("load_json", f"Successfully loaded {file_path}")
                else:
                    logger.error(f"Failed to load JSON from {file_path}")
                        
            except Exception as load_error:
                logger.error(f"Error loading JSON scenes: {load_error}")
                
        except Exception as e:
            logger.error(f"Error in handle_load_json: {e}")
    
    def handle_change_scene(self, address: str, *args):
        """
        Handle OSC message to change the active scene
        """
        try:
            if not args or len(args) == 0:
                logger.warning("Missing scene ID argument")
                return
            
            try:
                scene_id = int(args[0])
                
                with self._lock:
                    success = self.scene_manager.switch_scene(scene_id)
                    if success:
                        self._notify_state_change()
                
                if success:
                    logger.operation("change_scene", f"Scene changed to {scene_id}")
                else:
                    logger.warning(f"Failed to switch to scene: {scene_id}")
                    
            except ValueError:
                logger.error(f"Invalid scene ID: {args[0]}")
                
        except Exception as e:
            logger.error(f"Error in handle_change_scene: {e}")
    
    def handle_change_effect(self, address: str, *args):
        """
        Handle OSC message to change the current effect
        """
        try:
            if not args or len(args) == 0:
                logger.warning("Missing effect ID argument")
                return
            
            try:
                effect_id = int(args[0])
                
                with self._lock:
                    success = self.scene_manager.set_effect(effect_id)
                    if success:
                        self._notify_state_change()
                
                if success:
                    logger.operation("change_effect", f"Effect changed to {effect_id}")
                else:
                    logger.warning(f"Failed to set effect: {effect_id}")
                    
            except ValueError:
                logger.error(f"Invalid effect ID: {args[0]}")
                
        except Exception as e:
            logger.error(f"Error in handle_change_effect: {e}")
    
    def handle_change_palette(self, address: str, *args):
        """
        Handle OSC message to change the current palette
        """
        try:
            if not args or len(args) == 0:
                logger.warning("Missing palette ID argument")
                return
            
            palette_id = str(args[0])
            
            with self._lock:
                success = self.scene_manager.set_palette(palette_id)
                if success:
                    self._notify_state_change()
            
            if success:
                logger.operation("change_palette", f"Palette changed to {palette_id}")
            else:
                logger.warning(f"Failed to set palette: {palette_id}")
                
        except Exception as e:
            logger.error(f"Error in handle_change_palette: {e}")
    
    def handle_palette_color(self, address: str, palette_id: str, color_id: int, rgb: List[int]):
        """
        Handle OSC message to update a palette color
        """
        try:
            with self._lock:
                success = self.scene_manager.update_palette_color(palette_id, color_id, rgb)
                if success:
                    self._notify_state_change()
            
            if success:
                logger.operation("palette_color", f"Palette {palette_id}[{color_id}] = RGB({rgb[0]},{rgb[1]},{rgb[2]})")
            else:
                logger.warning(f"Failed to update palette {palette_id} color {color_id}")
                
        except Exception as e:
            logger.error(f"Error in handle_palette_color: {e}")
    
    def handle_set_dissolve_time(self, address: str, *args):
        """
        Handle OSC message to set dissolve time
        """
        try:
            if not args or len(args) == 0:
                logger.warning("Missing dissolve time argument")
                return
            
            try:
                dissolve_time = int(args[0])
                with self._lock:
                    self.dissolve_time = max(0, dissolve_time)
                    self._notify_state_change()
                logger.operation("set_dissolve_time", f"Dissolve time set to {self.dissolve_time}ms")
                
            except ValueError:
                logger.error(f"Invalid dissolve time: {args[0]}")
                
        except Exception as e:
            logger.error(f"Error in handle_set_dissolve_time: {e}")
    
    def handle_set_speed_percent(self, address: str, *args):
        """
        Handle OSC message to set animation speed percentage
        """
        try:
            if not args or len(args) == 0:
                logger.warning("Missing speed percent argument")
                return
            
            try:
                speed_percent = int(args[0])
                with self._lock:
                    self.speed_percent = max(0, min(200, speed_percent))
                    self._notify_state_change()
                logger.operation("set_speed_percent", f"Animation speed set to {self.speed_percent}%")
                
            except ValueError:
                logger.error(f"Invalid speed percent: {args[0]}")
                
        except Exception as e:
            logger.error(f"Error in handle_set_speed_percent: {e}")
    
    def handle_master_brightness(self, address: str, *args):
        """
        Handle OSC message for master brightness control
        """
        try:
            if not args or len(args) == 0:
                logger.warning("Missing brightness argument")
                return
            
            try:
                brightness = int(args[0])
                with self._lock:
                    self.master_brightness = max(0, min(255, brightness))
                    self._notify_state_change()
                logger.operation("master_brightness", f"Master brightness set to {self.master_brightness}")
                
            except ValueError:
                logger.error(f"Invalid brightness: {args[0]}")
                
        except Exception as e:
            logger.error(f"Error in handle_master_brightness: {e}")
    
    def handle_pattern_transition_config(self, address: str, *args):
        """
        Handle OSC message to configure pattern transitions
        """
        try:
            if len(args) < 3:
                logger.warning("Missing pattern transition config arguments. Expected: fade_in_ms fade_out_ms waiting_ms")
                return
            
            try:
                fade_in_ms = int(args[0])
                fade_out_ms = int(args[1])
                waiting_ms = int(args[2])
                
                self.scene_manager.set_transition_config(
                    fade_in_ms=fade_in_ms,
                    fade_out_ms=fade_out_ms,
                    waiting_ms=waiting_ms
                )
                
                logger.operation("pattern_transition_config", f"Config updated: fade_in={fade_in_ms}ms, fade_out={fade_out_ms}ms, waiting={waiting_ms}ms")
                
            except ValueError:
                logger.error(f"Invalid pattern transition config values: {args}")
                
        except Exception as e:
            logger.error(f"Error in handle_pattern_transition_config: {e}")