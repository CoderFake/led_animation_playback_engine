"""
LED Animation Playback Engine - Conditional animation loop
Animation only runs when scenes are loaded
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
from src.utils.logging import AnimationLogger, OSCLogger, LoggingUtils, PerformanceTracker
from src.utils.validation import ValidationUtils

logger = ComponentLogger("AnimationEngine")


@dataclass
class EngineStats:
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
    animation_running: bool = False


class DissolvePatternManager:
    
    def __init__(self):
        self.patterns: Dict[int, List[List[int]]] = {}
        self.current_pattern_id: int = 0
        self.enabled: bool = True
        
    def load_patterns_from_file(self, file_path: str) -> bool:
        try:
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                logger.error(f"Dissolve pattern file not found: {file_path}")
                return False
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if "dissolve_patterns" not in data:
                logger.error(f"File {file_path} missing 'dissolve_patterns' key")
                return False
            
            patterns_data = data["dissolve_patterns"]
            self.patterns.clear()
            
            for pattern_id_str, pattern_data in patterns_data.items():
                try:
                    pattern_id = int(pattern_id_str)
                    if isinstance(pattern_data, list):
                        self.patterns[pattern_id] = pattern_data
                        logger.debug(f"Loaded dissolve pattern {pattern_id}: {len(pattern_data)} transitions")
                    else:
                        logger.warning(f"Invalid pattern data format for pattern {pattern_id}")
                except ValueError:
                    logger.warning(f"Invalid pattern ID: {pattern_id_str}")
                    continue
            
            logger.info(f"Loaded {len(self.patterns)} dissolve patterns from {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading dissolve patterns: {e}")
            return False
    
    def get_pattern(self, pattern_id: int) -> Optional[List[List[int]]]:
        return self.patterns.get(pattern_id)
    
    def set_current_pattern(self, pattern_id: int) -> bool:
        if pattern_id in self.patterns:
            self.current_pattern_id = pattern_id
            logger.info(f"Current dissolve pattern set to {pattern_id}")
            return True
        else:
            logger.warning(f"Dissolve pattern {pattern_id} not found")
            return False
    
    def get_available_patterns(self) -> List[int]:
        return list(self.patterns.keys())

class AnimationEngine:
    
    def __init__(self):
        self.scene_manager = SceneManager()
        self.led_output = LEDOutput()
        self.osc_handler = OSCHandler(self)
        self.dissolve_manager = DissolvePatternManager()
        
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
        
        self.animation_running = False
        self.animation_should_stop = False
        
        self.stats.total_leds = EngineSettings.ANIMATION.led_count
        self.stats.target_fps = self.target_fps
        self.stats.master_brightness = self.master_brightness
        self.stats.speed_percent = self.speed_percent
        self.stats.dissolve_time = self.dissolve_time
        self.stats.animation_running = False
        
        self._setup_osc_handlers()
        
        logger.info(f"AnimationEngine initialized with conditional animation loop")
        logger.info(f"Target: {self.target_fps} FPS, {EngineSettings.ANIMATION.led_count} LEDs")
        logger.info(f"Animation will start only when scenes are loaded")
    
    def get_current_led_count(self) -> int:
        try:
            scene_info = self.scene_manager.get_current_scene_info()
            return scene_info.get('led_count', EngineSettings.ANIMATION.led_count)
        except Exception:
            return EngineSettings.ANIMATION.led_count
    
    def _setup_osc_handlers(self):
        handlers = {
            "/load_json": self.handle_load_json,
            "/change_scene": self.handle_change_scene,
            "/change_effect": self.handle_change_effect,
            "/change_palette": self.handle_change_palette,
            "/load_dissolve_json": self.handle_load_dissolve_json,
            "/set_dissolve_pattern": self.handle_set_dissolve_pattern,
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
            
            logger.info("Starting Performance Monitoring...")
            self._start_monitoring()
            
            self.running = True
            
            logger.info("Animation Engine started successfully")
            logger.info("Waiting for JSON scenes to be loaded before starting animation loop")
            
        except Exception as e:
            logger.error(f"Error starting engine: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise
    
    def _start_animation_loop(self):
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
            name="AnimationLoop"
        )
        self.animation_thread.start()
        
        logger.info("Animation loop started")
        
        time.sleep(0.1)
        if not self.animation_thread.is_alive():
            logger.error("Animation thread failed to start!")
            self.animation_running = False
            with self._lock:
                self.stats.animation_running = False
    
    def _stop_animation_loop(self):
        if not self.animation_running:
            return
        
        logger.info("Stopping animation loop...")
        
        self.animation_should_stop = True
        
        if self.animation_thread and self.animation_thread.is_alive():
            self.animation_thread.join(timeout=2.0)
            if self.animation_thread.is_alive():
                logger.warning("Animation thread did not stop gracefully")
        
        self.animation_running = False
        with self._lock:
            self.stats.animation_running = False
        
        logger.info("Animation loop stopped")
    
    def _check_scenes_available(self) -> bool:
        try:
            scene_info = self.scene_manager.get_current_scene_info()
            return scene_info.get('scene_id') is not None
        except Exception:
            return False
    
    async def stop(self):
        logger.info("Stopping Animation Engine...")
        
        self.running = False
        
        self._stop_animation_loop()
        
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
        try:
            logger.info(f"Animation loop started - Target: {self.target_fps} FPS")
            
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
                    self._update_frame(delta_time, frame_start)
                    
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
                
                if sleep_time > 0:
                    time.sleep(sleep_time)
            
            logger.info("Animation loop stopped")
        
        except Exception as e:
            logger.error(f"FATAL ERROR in animation loop: {e}")
            import traceback
            logger.error(f"Animation loop traceback: {traceback.format_exc()}")
        finally:
            self.animation_running = False
            with self._lock:
                self.stats.animation_running = False
    
    def _monitoring_loop(self):
        logger.debug("Performance monitoring loop started")
        
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
    
    def _log_fps_status(self):
        if self.fps_history:
            average_fps = sum(self.fps_history) / len(self.fps_history)
            
            with self._lock:
                self.stats.actual_fps = average_fps
            
            efficiency = (average_fps / self.target_fps) * 100
            
            logger.info(f"Frame {self.frame_count}: FPS {average_fps:.1f} ({efficiency:.1f}%), Speed {self.speed_percent}%, Active LEDs {self.stats.active_leds}")
            
            if efficiency < 90:
                logger.warning(f"Performance below target: {efficiency:.1f}%")
    
    def get_stats(self) -> EngineStats:
        with self._lock:
            stats_copy = EngineStats()
            stats_copy.target_fps = self.target_fps
            stats_copy.actual_fps = self.stats.actual_fps
            stats_copy.frame_count = self.frame_count
            stats_copy.animation_running = self.animation_running
            
            if self.animation_running:
                led_colors = self.scene_manager.get_led_output_with_timing(time.time())
                active_leds = sum(1 for color in led_colors if any(c > 0 for c in color[:3]))
                stats_copy.active_leds = active_leds
            else:
                stats_copy.active_leds = 0
                
            stats_copy.total_leds = self.get_current_led_count()
            stats_copy.animation_time = time.time() - self.engine_start_time
            stats_copy.master_brightness = self.master_brightness
            stats_copy.speed_percent = self.speed_percent
            stats_copy.dissolve_time = self.dissolve_time
            
            self.stats.active_leds = stats_copy.active_leds
            self.stats.total_leds = stats_copy.total_leds
            
            return stats_copy
    
    def _update_frame(self, delta_time: float, current_time: float):
        try:
            with self._lock:
                speed_percent = self.speed_percent
                master_brightness = self.master_brightness
            
            adjusted_delta = delta_time * (speed_percent / 100.0)
            
            scene_start = time.perf_counter()
            self.scene_manager.update_animation(adjusted_delta)
            
            led_start = time.perf_counter()
            led_colors = self.scene_manager.get_led_output_with_timing(current_time)
            
            if master_brightness < 255:
                brightness_factor = master_brightness / 255.0
                led_colors = [
                    [int(c * brightness_factor) for c in color]
                    for color in led_colors
                ]
            
            outpu_start = time.perf_counter()
            self.led_output.send_led_data(led_colors)
                
        except Exception as e:
            LoggingUtils.log_error("Animation", f"Error in _update_frame: {e}")
            import traceback
            LoggingUtils.log_error("Animation", f"Traceback: {traceback.format_exc()}")
    
    def add_state_callback(self, callback: Callable):
        self.state_callbacks.append(callback)
    
    def _notify_state_change(self):
        for callback in self.state_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"Error in state callback: {e}")
    
    def get_scene_info(self) -> Dict[str, Any]:
        return self.scene_manager.get_current_scene_info()
    
    def get_led_colors(self) -> List[List[int]]:
        if not self.animation_running:
            return [[0, 0, 0] for _ in range(self.get_current_led_count())]
            
        led_colors = self.scene_manager.get_led_output_with_timing(time.time())
        
        if self.master_brightness < 255:
            brightness_factor = self.master_brightness / 255.0
            led_colors = [
                [int(c * brightness_factor) for c in color]
                for color in led_colors
            ]
        
        return led_colors
    
    def handle_load_json(self, address: str, *args):
        try:
            OSCLogger.log_received(address, list(args))
            
            if not args or len(args) == 0:
                OSCLogger.log_validation_failed(address, "file_path", None, "non-empty string")
                return
            
            file_path = str(args[0])
            AnimationLogger.log_parameter_change("json_file", file_path)
            
            if not file_path.lower().endswith('.json'):
                file_path += '.json'
                LoggingUtils.log_info("Animation", f"Appended .json extension: {file_path}")
            
            success = False
            
            try:
                with self._lock:
                    if "multiple" in file_path.lower() or "scenes" in file_path.lower():
                        LoggingUtils.log_info("Animation", "Loading multiple scenes...")
                        success = self.scene_manager.load_multiple_scenes_from_file(file_path)
                    else:
                        LoggingUtils.log_info("Animation", "Loading single scene...")
                        success = self.scene_manager.load_scene_from_file(file_path)
                        
                    if not success:
                        LoggingUtils.log_info("Animation", "Retrying as multiple scenes...")
                        success = self.scene_manager.load_multiple_scenes_from_file(file_path)
                        
                if success:
                    self._notify_state_change()
                    scenes_count = len(self.scene_manager.scenes) if hasattr(self.scene_manager, 'scenes') else None
                    AnimationLogger.log_json_loaded("scenes", scenes_count)
                    
                    if not self.animation_running:
                        self._start_animation_loop()
                        LoggingUtils.log_info("Animation", "Animation loop started after loading scenes")
                    
                    OSCLogger.log_processed(address, "success")
                else:
                    OSCLogger.log_error(address, f"Failed to load JSON from {file_path}")
                        
            except Exception as load_error:
                OSCLogger.log_error(address, f"Error loading JSON scenes: {load_error}")
                
        except Exception as e:
            OSCLogger.log_error(address, f"Error in handle_load_json: {e}")
    
    def handle_load_dissolve_json(self, address: str, *args):
        try:
            logger.info(f"OSC received: {address} with args: {args}")
            
            if not args or len(args) == 0:
                logger.warning("Missing dissolve file path parameter")
                return
            
            file_path = str(args[0])
            logger.info(f"Loading dissolve patterns from: {file_path}")
            
            if not file_path.lower().endswith('.json'):
                file_path += '.json'
                logger.info(f"Appended .json extension: {file_path}")
            
            success = self.dissolve_manager.load_patterns_from_file(file_path)
            
            if success:
                available_patterns = self.dissolve_manager.get_available_patterns()
                logger.operation("load_dissolve_json", f"Successfully loaded dissolve patterns from {file_path}")
                logger.info(f"Available patterns: {available_patterns}")
                
                self.scene_manager.load_dissolve_patterns(self.dissolve_manager.patterns)
                
                self._notify_state_change()
            else:
                logger.error(f"Failed to load dissolve patterns from {file_path}")
                
        except Exception as e:
            logger.error(f"Error in handle_load_dissolve_json: {e}")
    
    def handle_set_dissolve_pattern(self, address: str, *args):
        try:
            logger.info(f"OSC received: {address} with args: {args}")
            
            if not args or len(args) == 0:
                logger.warning("Missing pattern ID parameter")
                return
            
            try:
                pattern_id = int(args[0])
                logger.info(f"Setting dissolve pattern to: {pattern_id}")
                
                available_patterns = self.dissolve_manager.get_available_patterns()
                if pattern_id not in available_patterns and available_patterns:
                    logger.warning(f"Pattern ID {pattern_id} invalid. Available patterns: {available_patterns}")
                    return
                
                success = self.dissolve_manager.set_current_pattern(pattern_id)
                
                if success:
                    scene_success = self.scene_manager.set_dissolve_pattern(pattern_id)
                    
                    if scene_success:
                        logger.operation("set_dissolve_pattern", f"Successfully set pattern to {pattern_id}")
                        self._notify_state_change()
                    else:
                        logger.warning(f"Failed to set pattern in scene manager: {pattern_id}")
                else:
                    logger.warning(f"Failed to set pattern: {pattern_id}")
                    
            except ValueError:
                logger.error(f"Invalid pattern ID: {args[0]} (must be an integer)")
                
        except Exception as e:
            logger.error(f"Error in handle_set_dissolve_pattern: {e}")
    
    def handle_change_scene(self, address: str, *args):
        try:
            OSCLogger.log_received(address, list(args))
            
            if not args or len(args) == 0:
                OSCLogger.log_validation_failed(address, "scene_id", None, "integer")
                return
            
            try:
                scene_id = int(args[0])
                
                scene_info = self.scene_manager.get_current_scene_info()
                available_scenes = scene_info.get('available_scenes', [])
                if available_scenes and scene_id not in available_scenes:
                    OSCLogger.log_validation_failed(address, "scene_id", scene_id, f"one of {available_scenes}")
                    return
                
                with self._lock:
                    dissolve_info = self.scene_manager.get_dissolve_info()
                    use_dissolve = dissolve_info.get('enabled', False)
                    
                    success = self.scene_manager.switch_scene(scene_id, use_dissolve=use_dissolve)
                    if success:
                        self._notify_state_change()
                
                if success:
                    transition_type = "dissolve" if use_dissolve else "direct"
                    AnimationLogger.log_scene_change(scene_id)
                    OSCLogger.log_processed(address, f"success using {transition_type}")
                else:
                    OSCLogger.log_error(address, f"Failed to change scene to: {scene_id}")
                    
            except ValueError:
                OSCLogger.log_validation_failed(address, "scene_id", args[0], "integer")
                
        except Exception as e:
            OSCLogger.log_error(address, f"Error in handle_change_scene: {e}")
    
    def handle_change_effect(self, address: str, *args):
        try:
            logger.info(f"OSC received: {address} with args: {args}")
            
            if not args or len(args) == 0:
                logger.warning("Missing effect ID parameter")
                return
            
            try:
                effect_id = int(args[0])
                logger.info(f"Changing effect to: {effect_id}")
            
                scene_info = self.scene_manager.get_current_scene_info()
                available_effects = scene_info.get('available_effects', [])
                if available_effects and effect_id not in available_effects:
                    logger.warning(f"Effect ID {effect_id} invalid. Available effects: {available_effects}")
                
                with self._lock:
                    dissolve_info = self.scene_manager.get_dissolve_info()
                    use_dissolve = dissolve_info.get('enabled', False)
                    
                    success = self.scene_manager.set_effect(effect_id, use_dissolve=use_dissolve)
                    if success:
                        self._notify_state_change()
                
                if success:
                    transition_type = "dissolve" if use_dissolve else "pattern/direct"
                    logger.operation("change_effect", f"Successfully changed effect to {effect_id} using {transition_type}")
                else:
                    logger.warning(f"Failed to change effect to: {effect_id}")
                    
            except ValueError:
                logger.error(f"Invalid effect ID: {args[0]} (must be an integer)")
                
        except Exception as e:
            logger.error(f"Error in handle_change_effect: {e}")
    
    def handle_change_palette(self, address: str, *args):
        try:
            logger.info(f"OSC received: {address} with args: {args}")
            
            if not args or len(args) == 0:
                logger.warning("Missing palette ID parameter")
                return
            
            try:
                palette_id = int(args[0])
                logger.info(f"Changing palette to: {palette_id}")
            
                scene_info = self.scene_manager.get_current_scene_info()
                available_palettes = scene_info.get('available_palettes', [])
                if available_palettes and palette_id not in available_palettes:
                    logger.warning(f"Palette ID {palette_id} invalid. Available palettes: {available_palettes}")
                
                with self._lock:
                    dissolve_info = self.scene_manager.get_dissolve_info()
                    use_dissolve = dissolve_info.get('enabled', False)
                    
                    success = self.scene_manager.set_palette(palette_id, use_dissolve=use_dissolve)
                    if success:
                        self._notify_state_change()
                
                if success:
                    transition_type = "dissolve" if use_dissolve else "pattern/direct"
                    logger.operation("change_palette", f"Successfully changed palette to {palette_id} using {transition_type}")
                else:
                    logger.warning(f"Failed to change palette to: {palette_id}")
                    
            except ValueError:
                logger.error(f"Invalid palette ID: {args[0]} (must be an integer)")
                
        except Exception as e:
            logger.error(f"Error in handle_change_palette: {e}")
    
    def handle_palette_color(self, address: str, palette_id: str, color_id: int, rgb: List[int]):
        try:
            logger.info(f"OSC received: {address} with palette_id: {palette_id}, color_id: {color_id}, rgb: {rgb}")
            
            if isinstance(palette_id, str):
                palette_int_id = ord(palette_id.upper()) - ord('A') if palette_id else 0
                logger.info(f"Converted palette_id from '{palette_id}' to {palette_int_id}")
            else:
                palette_int_id = int(palette_id)
                logger.info(f"Using palette_id: {palette_int_id}")
        
            if palette_int_id < 0 or palette_int_id > 4:
                logger.warning(f"Invalid palette ID {palette_int_id} (must be 0-4)")
                return
            
            if color_id < 0 or color_id > 5:
                logger.warning(f"Invalid color ID {color_id} (must be 0-5)")
                return
            
            if len(rgb) != 3:
                logger.warning(f"Invalid RGB values: {rgb} (must have 3 values)")
                return
            
            validated_rgb = []
            for i, value in enumerate(rgb):
                if not isinstance(value, int) or value < 0 or value > 255:
                    logger.warning(f"Invalid RGB[{i}] = {value} (must be 0-255)")
                    return
                validated_rgb.append(value)
            
            logger.info(f"Updating palette {palette_int_id} color {color_id} to RGB({validated_rgb[0]},{validated_rgb[1]},{validated_rgb[2]})")
            
            with self._lock:
                success = self.scene_manager.update_palette_color(palette_int_id, color_id, validated_rgb)
                if success:
                    self._notify_state_change()
            
            if success:
                logger.operation("palette_color", f"Successfully updated palette {palette_int_id}[{color_id}] = RGB({validated_rgb[0]},{validated_rgb[1]},{validated_rgb[2]})")
            else:
                logger.warning(f"Failed to update palette {palette_int_id} color {color_id}")
                
        except Exception as e:
            logger.error(f"Error in handle_palette_color: {e}")
    
    def handle_set_dissolve_time(self, address: str, *args):
        try:
            logger.info(f"OSC received: {address} with args: {args}")
            
            if not args or len(args) == 0:
                logger.warning("Missing dissolve time parameter")
                return
            
            try:
                dissolve_time = int(args[0])
                logger.info(f"Setting dissolve time to: {dissolve_time}ms")
                
                if dissolve_time < 0:
                    logger.warning(f"Invalid dissolve time {dissolve_time} (must be >= 0)")
                    dissolve_time = 0
                
                if dissolve_time > 60000: 
                    logger.warning(f"Dissolve time {dissolve_time}ms is too large, capping at 60000ms")
                    dissolve_time = 60000
                
                with self._lock:
                    old_time = self.dissolve_time
                    self.dissolve_time = dissolve_time
                    self._notify_state_change()
                
                logger.operation("set_dissolve_time", f"Successfully set dissolve time from {old_time}ms to {self.dissolve_time}ms")
                
            except ValueError:
                logger.error(f"Invalid dissolve time: {args[0]} (must be an integer)")
                
        except Exception as e:
            logger.error(f"Error in handle_set_dissolve_time: {e}")
    
    def handle_set_speed_percent(self, address: str, *args):
        try:
            logger.info(f"OSC received: {address} with args: {args}")
            
            if not args or len(args) == 0:
                logger.warning("Missing speed percent parameter")
                return
            
            try:
                speed_percent = int(args[0])
                logger.info(f"Setting animation speed to: {speed_percent}%")
                
                if speed_percent < 0:
                    logger.warning(f"Invalid speed percent {speed_percent} (must be >= 0)")
                    speed_percent = 0
                
                if speed_percent > 1023:
                    logger.warning(f"Invalid speed percent {speed_percent} (must be <= 1023)")
                    speed_percent = 1023
                
                with self._lock:
                    old_speed = self.speed_percent
                    self.speed_percent = speed_percent
                    self._notify_state_change()
                
                logger.operation("set_speed_percent", f"Successfully set animation speed from {old_speed}% to {self.speed_percent}%")
                
            except ValueError:
                logger.error(f"Invalid speed percent: {args[0]} (must be an integer)")
                
        except Exception as e:
            logger.error(f"Error in handle_set_speed_percent: {e}")
    
    def handle_master_brightness(self, address: str, *args):
        try:
            logger.info(f"OSC received: {address} with args: {args}")
            
            if not args or len(args) == 0:
                logger.warning("Missing brightness parameter")
                return
            
            try:
                brightness = int(args[0])
                logger.info(f"Setting master brightness to: {brightness}")
                
                # Validate brightness (0-255)
                if brightness < 0:
                    logger.warning(f"Invalid brightness {brightness} (must be >= 0)")
                    brightness = 0
                
                if brightness > 255:
                    logger.warning(f"Invalid brightness {brightness} (must be <= 255)")
                    brightness = 255
                
                with self._lock:
                    old_brightness = self.master_brightness
                    self.master_brightness = brightness
                    self._notify_state_change()
                
                logger.operation("master_brightness", f"Successfully set master brightness from {old_brightness} to {self.master_brightness}")
                
            except ValueError:
                logger.error(f"Invalid brightness: {args[0]} (must be an integer)")
                
        except Exception as e:
            logger.error(f"Error in handle_master_brightness: {e}")
    
    def handle_pattern_transition_config(self, address: str, *args):
        try:
            logger.info(f"OSC received: {address} with args: {args}")
            
            if len(args) < 3:
                logger.warning("Missing pattern transition config parameters. Expected: fade_in_ms fade_out_ms waiting_ms")
                return
            
            try:
                fade_in_ms = int(args[0])
                fade_out_ms = int(args[1])
                waiting_ms = int(args[2])
                
                logger.info(f"Configuring pattern transition: fade_in={fade_in_ms}ms, fade_out={fade_out_ms}ms, waiting={waiting_ms}ms")
                
                if fade_in_ms < 0:
                    logger.warning(f"Invalid fade_in_ms {fade_in_ms} (must be >= 0)")
                    fade_in_ms = 0
                
                if fade_out_ms < 0:
                    logger.warning(f"Invalid fade_out_ms {fade_out_ms} (must be >= 0)")
                    fade_out_ms = 0
                
                if waiting_ms < 0:
                    logger.warning(f"Invalid waiting_ms {waiting_ms} (must be >= 0)")
                    waiting_ms = 0
                
                self.scene_manager.set_transition_config(
                    fade_in_ms=fade_in_ms,
                    fade_out_ms=fade_out_ms,
                    waiting_ms=waiting_ms
                )
                
                logger.operation("pattern_transition_config", f"Successfully configured: fade_in={fade_in_ms}ms, fade_out={fade_out_ms}ms, waiting={waiting_ms}ms")
                
            except ValueError:
                logger.error(f"Invalid pattern transition config values: {args} (must be integers)")
                
        except Exception as e:
            logger.error(f"Error in handle_pattern_transition_config: {e}")
    
    def get_dissolve_info(self) -> Dict[str, Any]:
        """Get dissolve system information"""
        dissolve_manager_info = {
            "manager_enabled": self.dissolve_manager.enabled,
            "manager_current_pattern_id": self.dissolve_manager.current_pattern_id,
            "manager_available_patterns": self.dissolve_manager.get_available_patterns(),
            "manager_pattern_count": len(self.dissolve_manager.patterns)
        }
        
        scene_dissolve_info = self.scene_manager.get_dissolve_info()
        
        return {
            **dissolve_manager_info,
            **scene_dissolve_info
        }
