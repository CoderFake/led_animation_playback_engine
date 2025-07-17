"""
Scene Manager - Improved transition handling and LED count management
Supports zero-origin IDs, time-based rendering, and dynamic LED counts
"""

import time
import threading
import json
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

from src.models.scene import Scene
from config.settings import EngineSettings
from src.utils.logger import ComponentLogger
from src.utils.color_utils import ColorUtils
from src.models.common import PatternTransition, PatternTransitionConfig, DissolveTransition
from src.models.types import TransitionPhase, DissolvePhase


logger = ComponentLogger("SceneManager")

class SceneManager:
    """
    Manages animation scenes with improved transition handling and dynamic LED counts
    Supports zero-origin IDs, time-based rendering, and stable brightness calculations
    """
    
    def __init__(self):
        self.scenes: Dict[int, Scene] = {}
        self.active_scene_id: Optional[int] = None
        self.last_update_time = time.time()
        
        self._lock = threading.RLock()
        self._debug_frame_count = 0
        self._change_callbacks: List[Callable] = []
        
        self.pattern_transition = PatternTransition()
        self.transition_config = PatternTransitionConfig(
            fade_in_ms=EngineSettings.PATTERN_TRANSITION.default_fade_in_ms,
            fade_out_ms=EngineSettings.PATTERN_TRANSITION.default_fade_out_ms,
            waiting_ms=EngineSettings.PATTERN_TRANSITION.default_waiting_ms
        )
        
        self.dissolve_transition = DissolveTransition()
        self.dissolve_patterns: Dict[int, List[List[int]]] = {}
        self.current_dissolve_pattern_id = 0
        
        self.stats = {
            'scenes_loaded': 0,
            'scene_switches': 0,
            'effect_changes': 0,
            'palette_changes': 0,
            'transitions_completed': 0,
            'dissolve_transitions_completed': 0,
            'errors': 0
        }
        
        logger.info("SceneManager initialized with zero-origin ID system")
        logger.info(f"Pattern transitions: {'enabled' if EngineSettings.PATTERN_TRANSITION.enabled else 'disabled'}")
        logger.info("Dissolve pattern system initialized")
    
    async def initialize(self):
        """Initialize the scene manager"""
        logger.info("Initializing Scene Manager...")
        logger.info("Scene Manager initialization complete")
        logger.info("Ready to receive OSC commands for scene loading")
    
    def add_change_callback(self, callback: Callable):
        """Add callback for scene changes"""
        with self._lock:
            self._change_callbacks.append(callback)
    
    def _notify_changes(self):
        """Notify all registered callbacks of scene changes"""
        for callback in self._change_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"Error in change callback: {e}")
    
    def set_transition_config(self, fade_in_ms: int = None, fade_out_ms: int = None, waiting_ms: int = None):
        """Update transition configuration"""
        with self._lock:
            if fade_in_ms is not None:
                self.transition_config.fade_in_ms = fade_in_ms
            if fade_out_ms is not None:
                self.transition_config.fade_out_ms = fade_out_ms
            if waiting_ms is not None:
                self.transition_config.waiting_ms = waiting_ms
                
            logger.info(f"Transition config updated: fade_in={self.transition_config.fade_in_ms}ms, "
                       f"fade_out={self.transition_config.fade_out_ms}ms, waiting={self.transition_config.waiting_ms}ms")
    
    def load_dissolve_patterns(self, patterns: Dict[int, List[List[int]]]) -> bool:
        """Load dissolve patterns from animation engine"""
        try:
            with self._lock:
                self.dissolve_patterns = patterns.copy()
                logger.info(f"Loaded {len(self.dissolve_patterns)} dissolve patterns")
                logger.info(f"Available pattern IDs: {list(self.dissolve_patterns.keys())}")
                return True
        except Exception as e:
            logger.error(f"Error loading dissolve patterns: {e}")
            return False
    
    def set_dissolve_pattern(self, pattern_id: int) -> bool:
        """Set current dissolve pattern"""
        try:
            with self._lock:
                if pattern_id in self.dissolve_patterns:
                    self.current_dissolve_pattern_id = pattern_id
                    logger.info(f"Dissolve pattern set to {pattern_id}")
                    return True
                else:
                    available = list(self.dissolve_patterns.keys())
                    logger.warning(f"Dissolve pattern {pattern_id} not found. Available: {available}")
                    return False
        except Exception as e:
            logger.error(f"Error setting dissolve pattern: {e}")
            return False
    
    def start_dissolve_transition(self, to_scene_id: int = None, to_effect_id: int = None, to_palette_id: int = None) -> bool:
        """Start dissolve transition using current pattern"""
        try:
            with self._lock:
                if self.current_dissolve_pattern_id not in self.dissolve_patterns:
                    logger.warning(f"No dissolve pattern {self.current_dissolve_pattern_id} available")
                    return False
                
                if self.active_scene_id is None or self.active_scene_id not in self.scenes:
                    logger.warning("Cannot start dissolve transition: no active scene")
                    return False
                
                current_scene = self.scenes[self.active_scene_id]
                pattern_data = self.dissolve_patterns[self.current_dissolve_pattern_id]
                
                self.dissolve_transition.from_scene_id = self.active_scene_id
                self.dissolve_transition.from_effect_id = current_scene.current_effect_id
                self.dissolve_transition.from_palette_id = current_scene.current_palette_id
                
                self.dissolve_transition.to_scene_id = to_scene_id if to_scene_id is not None else self.active_scene_id
                self.dissolve_transition.to_effect_id = to_effect_id if to_effect_id is not None else current_scene.current_effect_id
                self.dissolve_transition.to_palette_id = to_palette_id if to_palette_id is not None else current_scene.current_palette_id
                
                self.dissolve_transition.pattern_id = self.current_dissolve_pattern_id
                
                led_count = current_scene.led_count
                self.dissolve_transition.start_dissolve(pattern_data, led_count)
                
                logger.operation("dissolve_transition_start", 
                               f"Pattern {self.current_dissolve_pattern_id}: "
                               f"Effect {self.dissolve_transition.from_effect_id}→{self.dissolve_transition.to_effect_id}, "
                               f"Palette {self.dissolve_transition.from_palette_id}→{self.dissolve_transition.to_palette_id}")
                
                return True
                
        except Exception as e:
            logger.error(f"Error starting dissolve transition: {e}")
            return False
    
    def start_pattern_transition(self, to_effect_id: int = None, to_palette_id: int = None):
        """Start a pattern transition between effects/palettes (zero-origin IDs)"""
        with self._lock:
            if self.active_scene_id is None or self.active_scene_id not in self.scenes:
                logger.warning("Cannot start transition: no active scene")
                return False
            
            current_scene = self.scenes[self.active_scene_id]
            
            self.pattern_transition.is_active = True
            self.pattern_transition.phase = TransitionPhase.FADE_OUT
            
            self.pattern_transition.from_effect_id = current_scene.current_effect_id
            self.pattern_transition.from_palette_id = current_scene.current_palette_id
            self.pattern_transition.to_effect_id = to_effect_id if to_effect_id is not None else current_scene.current_effect_id
            self.pattern_transition.to_palette_id = to_palette_id if to_palette_id is not None else current_scene.current_palette_id
            
            self.pattern_transition.fade_in_ms = self.transition_config.fade_in_ms
            self.pattern_transition.fade_out_ms = self.transition_config.fade_out_ms
            self.pattern_transition.waiting_ms = self.transition_config.waiting_ms
            
            self.pattern_transition.start_time = time.time()
            self.pattern_transition.phase_start_time = time.time()
            self.pattern_transition.progress = 0.0
            
            logger.operation("pattern_transition_start", 
                           f"Effect {self.pattern_transition.from_effect_id}→{self.pattern_transition.to_effect_id}, "
                           f"Palette {self.pattern_transition.from_palette_id}→{self.pattern_transition.to_palette_id}")
            return True
    
    def _update_pattern_transition(self, current_time: float):
        """Update active pattern transition state with improved timing"""
        if not self.pattern_transition.is_active:
            return
            
        phase_elapsed = (current_time - self.pattern_transition.phase_start_time) * 1000
        
        if self.pattern_transition.phase == TransitionPhase.FADE_OUT:
            if phase_elapsed >= self.pattern_transition.fade_out_ms:
                self.pattern_transition.phase = TransitionPhase.WAITING
                self.pattern_transition.phase_start_time = current_time
                logger.debug("Transition: FADE_OUT → WAITING")
            else:
                if self.pattern_transition.fade_out_ms > 0:
                    progress = phase_elapsed / self.pattern_transition.fade_out_ms
                    self.pattern_transition.progress = max(EngineSettings.PATTERN_TRANSITION.minimum_transition_brightness, 
                                                         1.0 - progress)
                else:
                    self.pattern_transition.progress = 0.0
        
        elif self.pattern_transition.phase == TransitionPhase.WAITING:
            if phase_elapsed >= self.pattern_transition.waiting_ms:
                self.pattern_transition.phase = TransitionPhase.FADE_IN
                self.pattern_transition.phase_start_time = current_time
                logger.debug("Transition: WAITING → FADE_IN")
            else:
                self.pattern_transition.progress = 0.0
        
        elif self.pattern_transition.phase == TransitionPhase.FADE_IN:
            if phase_elapsed >= self.pattern_transition.fade_in_ms:
                self._complete_pattern_transition()
            else:
                if self.pattern_transition.fade_in_ms > 0:
                    progress = phase_elapsed / self.pattern_transition.fade_in_ms
                    self.pattern_transition.progress = max(EngineSettings.PATTERN_TRANSITION.minimum_transition_brightness, 
                                                         progress)
                else:
                    self.pattern_transition.progress = 1.0
    
    def _complete_pattern_transition(self):
        """Complete the active pattern transition"""
        if self.active_scene_id is None or self.active_scene_id not in self.scenes:
            return
            
        scene = self.scenes[self.active_scene_id]
        scene.current_effect_id = self.pattern_transition.to_effect_id
        scene.current_palette_id = self.pattern_transition.to_palette_id
        
        self.pattern_transition.is_active = False
        self.pattern_transition.phase = TransitionPhase.COMPLETED
        
        self.stats['transitions_completed'] += 1
        
        logger.operation("pattern_transition_complete", 
                        f"Effect {self.pattern_transition.to_effect_id}, "
                        f"Palette {self.pattern_transition.to_palette_id}")
        self._notify_changes()
    
    def get_led_output_with_timing(self, current_time: float) -> List[List[int]]:
        """Get LED output with time-based brightness and dynamic LED count"""
        with self._lock:
            if self.dissolve_transition.is_active:
                return self._get_dissolve_led_output_with_timing(current_time)
            elif self.pattern_transition.is_active:
                return self._get_transition_led_output_with_timing(current_time)
            else:
                if self.active_scene_id is not None and self.active_scene_id in self.scenes:
                    scene = self.scenes[self.active_scene_id]
                    return scene.get_led_output_with_timing(current_time)
                return [[0, 0, 0] for _ in range(EngineSettings.ANIMATION.led_count)]
    
    def get_led_output(self) -> List[List[int]]:
        """Get current LED output (legacy method)"""
        return self.get_led_output_with_timing(time.time())
    
    def _get_transition_led_output_with_timing(self, current_time: float) -> List[List[int]]:
        """Generate LED output during transitions with improved brightness handling"""
        if self.active_scene_id is None or self.active_scene_id not in self.scenes:
            return [[0, 0, 0] for _ in range(EngineSettings.ANIMATION.led_count)]
        
        scene = self.scenes[self.active_scene_id]
        led_count = scene.led_count
        
        if self.pattern_transition.phase == TransitionPhase.FADE_OUT:
            scene.current_effect_id = self.pattern_transition.from_effect_id
            scene.current_palette_id = self.pattern_transition.from_palette_id
            output = scene.get_led_output_with_timing(current_time)
            
            brightness = self.pattern_transition.progress
            return [
                ColorUtils.apply_brightness(color, brightness)
                for color in output
            ]
        
        elif self.pattern_transition.phase == TransitionPhase.WAITING:
            return [[0, 0, 0] for _ in range(led_count)]
        
        elif self.pattern_transition.phase == TransitionPhase.FADE_IN:
            scene.current_effect_id = self.pattern_transition.to_effect_id
            scene.current_palette_id = self.pattern_transition.to_palette_id
            output = scene.get_led_output_with_timing(current_time)
            
            brightness = self.pattern_transition.progress
            return [
                ColorUtils.apply_brightness(color, brightness)
                for color in output
            ]
        
        return [[0, 0, 0] for _ in range(led_count)]
    
    def _get_dissolve_led_output_with_timing(self, current_time: float) -> List[List[int]]:
        """Generate LED output during dissolve transitions"""
        if not self.dissolve_transition.is_active:
            return [[0, 0, 0] for _ in range(EngineSettings.ANIMATION.led_count)]
        
        try:
            from_scene_id = self.dissolve_transition.from_scene_id
            from_effect_id = self.dissolve_transition.from_effect_id
            from_palette_id = self.dissolve_transition.from_palette_id
            
            to_scene_id = self.dissolve_transition.to_scene_id
            to_effect_id = self.dissolve_transition.to_effect_id
            to_palette_id = self.dissolve_transition.to_palette_id
            
            from_colors = [[0, 0, 0] for _ in range(self.dissolve_transition.led_count)]
            if from_scene_id in self.scenes:
                from_scene = self.scenes[from_scene_id]
                old_effect_id = from_scene.current_effect_id
                old_palette_id = from_scene.current_palette_id
                from_scene.current_effect_id = from_effect_id
                from_scene.current_palette_id = from_palette_id
                from_colors = from_scene.get_led_output_with_timing(current_time)

                from_scene.current_effect_id = old_effect_id
                from_scene.current_palette_id = old_palette_id
            
            to_colors = [[0, 0, 0] for _ in range(self.dissolve_transition.led_count)]
            if to_scene_id in self.scenes:
                to_scene = self.scenes[to_scene_id]
                old_effect_id = to_scene.current_effect_id
                old_palette_id = to_scene.current_palette_id
                to_scene.current_effect_id = to_effect_id
                to_scene.current_palette_id = to_palette_id
                to_colors = to_scene.get_led_output_with_timing(current_time)

                to_scene.current_effect_id = old_effect_id
                to_scene.current_palette_id = old_palette_id
            
            self.dissolve_transition.update_dissolve(current_time, from_colors, to_colors)

            output = self.dissolve_transition.get_led_output(from_colors, to_colors)
            
            if not self.dissolve_transition.is_active:
                if to_scene_id != self.active_scene_id:
                    self.active_scene_id = to_scene_id
                if to_scene_id in self.scenes:
                    to_scene = self.scenes[to_scene_id]
                    to_scene.current_effect_id = to_effect_id
                    to_scene.current_palette_id = to_palette_id
                
                self.stats['dissolve_transitions_completed'] += 1
                logger.operation("dissolve_transition_complete", 
                               f"Scene {to_scene_id}, Effect {to_effect_id}, Palette {to_palette_id}")
                self._notify_changes()
            
            return output
            
        except Exception as e:
            logger.error(f"Error in dissolve LED output: {e}")
            self.dissolve_transition.is_active = False
            return [[0, 0, 0] for _ in range(EngineSettings.ANIMATION.led_count)]
    
    def load_scene_from_file(self, file_path: str) -> bool:
        """Load a single scene from JSON file"""
        try:
            with self._lock:
                file_path_obj = Path(file_path)
                if not file_path_obj.exists():
                    logger.error(f"Scene file not found: {file_path}")
                    return False
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if "scene_id" in data or "scene_ID" in data:
                    scene = Scene.from_dict(data)
                    self.scenes[scene.scene_id] = scene
                    
                    if self.active_scene_id is None:
                        self.active_scene_id = scene.scene_id
                    
                    self.stats['scenes_loaded'] += 1
                    
                    logger.operation("load_single_scene", f"Scene {scene.scene_id} from {file_path}")
                    self._log_scene_status()
                    self._notify_changes()
                    return True
                else:
                    logger.warning(f"File {file_path} missing scene_id - not a valid single scene format")
                    return False
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in {file_path}: {e}")
            self.stats['errors'] += 1
            return False
        except Exception as e:
            logger.error(f"Error loading single scene from {file_path}: {e}")
            self.stats['errors'] += 1
            return False
    
    def load_multiple_scenes_from_file(self, file_path: str) -> bool:
        """Load multiple scenes from JSON file"""
        try:
            with self._lock:
                file_path_obj = Path(file_path)
                if not file_path_obj.exists():
                    logger.error(f"Scene file not found: {file_path}")
                    return False
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if "scenes" not in data:
                    logger.warning(f"File {file_path} does not contain 'scenes' array")
                    return False
                
                scenes_data = data.get("scenes", [])
                if not scenes_data:
                    logger.warning(f"File {file_path} has empty 'scenes' array")
                    return False
                
                loaded_count = 0
                
                for scene_data in scenes_data:
                    try:
                        if "scene_id" not in scene_data and "scene_ID" not in scene_data:
                            logger.warning(f"Scene data missing scene_id: {scene_data}")
                            continue
                            
                        scene = Scene.from_dict(scene_data)
                        self.scenes[scene.scene_id] = scene
                        loaded_count += 1
                        
                        if self.active_scene_id is None:
                            self.active_scene_id = scene.scene_id
                            
                    except Exception as e:
                        logger.error(f"Error loading individual scene: {e}")
                        self.stats['errors'] += 1
                        continue
                
                if loaded_count > 0:
                    self.stats['scenes_loaded'] += loaded_count
                    logger.operation("load_multiple_scenes", f"Loaded {loaded_count} scenes from {file_path}")
                    self._log_scene_status()
                    self._notify_changes()
                    return True
                else:
                    logger.error(f"No valid scenes loaded from {file_path}")
                    self.stats['errors'] += 1
                    return False
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in {file_path}: {e}")
            self.stats['errors'] += 1
            return False
        except Exception as e:
            logger.error(f"Error loading multiple scenes from {file_path}: {e}")
            self.stats['errors'] += 1
            return False
    
    def set_effect(self, effect_id: int, use_dissolve: bool = False) -> bool:
        """Set effect for active scene using zero-origin ID"""
        try:
            with self._lock:
                if self.active_scene_id is None or self.active_scene_id not in self.scenes:
                    logger.warning("No active scene for effect change")
                    return False
                
                scene = self.scenes[self.active_scene_id]
                if not (0 <= effect_id < len(scene.effects)):
                    available_effects = list(range(len(scene.effects)))
                    logger.warning(f"Effect {effect_id} not found in scene {self.active_scene_id}. Available: {available_effects}")
                    return False
                
                if use_dissolve and self.dissolve_patterns:
                    success = self.start_dissolve_transition(to_effect_id=effect_id)
                    if success:
                        self.stats['effect_changes'] += 1
                        return True
                
                if EngineSettings.PATTERN_TRANSITION.enabled:
                    success = self.start_pattern_transition(to_effect_id=effect_id)
                    if success:
                        self.stats['effect_changes'] += 1
                    return success
                else:
                    scene.current_effect_id = effect_id
                    self.stats['effect_changes'] += 1
                    logger.operation("set_effect", f"Effect {effect_id} for scene {self.active_scene_id}")
                    self._notify_changes()
                    return True
                
        except Exception as e:
            logger.error(f"Error setting effect: {e}")
            self.stats['errors'] += 1
            return False
    
    def set_palette(self, palette_id: int, use_dissolve: bool = False) -> bool:
        """Set palette for active scene using zero-origin ID"""
        try:
            with self._lock:
                if self.active_scene_id is None or self.active_scene_id not in self.scenes:
                    logger.warning("No active scene for palette change")
                    return False
                
                scene = self.scenes[self.active_scene_id]
                if not (0 <= palette_id < len(scene.palettes)):
                    available_palettes = list(range(len(scene.palettes)))
                    logger.warning(f"Palette {palette_id} not found in scene {self.active_scene_id}. Available: {available_palettes}")
                    return False
                
                if use_dissolve and self.dissolve_patterns:
                    success = self.start_dissolve_transition(to_palette_id=palette_id)
                    if success:
                        self.stats['palette_changes'] += 1
                        return True
                
                if EngineSettings.PATTERN_TRANSITION.enabled:
                    success = self.start_pattern_transition(to_palette_id=palette_id)
                    if success:
                        self.stats['palette_changes'] += 1
                    return success
                else:
                    scene.current_palette_id = palette_id
                    self.stats['palette_changes'] += 1
                    logger.operation("set_palette", f"Palette {palette_id} for scene {self.active_scene_id}")
                    self._notify_changes()
                    return True
                
        except Exception as e:
            logger.error(f"Error setting palette: {e}")
            self.stats['errors'] += 1
            return False
    
    def update_palette_color(self, palette_id: int, color_id: int, rgb: List[int]) -> bool:
        """Update specific color in palette using zero-origin IDs"""
        try:
            with self._lock:
                if self.active_scene_id is None or self.active_scene_id not in self.scenes:
                    logger.warning("No active scene for palette color update")
                    return False
                
                scene = self.scenes[self.active_scene_id]
                success = scene.update_palette_color(palette_id, color_id, rgb)
                
                if success:
                    logger.operation("update_palette_color", 
                                   f"Palette {palette_id}[{color_id}] = RGB({rgb[0]},{rgb[1]},{rgb[2]})")
                    self._notify_changes()
                else:
                    logger.warning(f"Failed to update palette {palette_id} color {color_id}")
                
                return success
                
        except Exception as e:
            logger.error(f"Error updating palette color: {e}")
            self.stats['errors'] += 1
            return False
    
    def update_animation_frame(self):
        """Update animation frame"""
        current_time = time.time()
        delta_time = current_time - self.last_update_time
        self.last_update_time = current_time
        
        self.update_animation(delta_time)
    
    def update_animation(self, delta_time: float):
        """Update animation state for all scenes"""
        with self._lock:
            current_time = time.time()
            
            self._update_pattern_transition(current_time)
            
            self._debug_frame_count += 1
            
            if self._debug_frame_count % 1800 == 0:
                self._log_animation_status()
            
            for scene in self.scenes.values():
                for effect in scene.effects:
                    effect.update_animation(delta_time)
    
    def _log_animation_status(self):
        """Log animation status for debugging"""
        if self.active_scene_id is None or self.active_scene_id not in self.scenes:
            return
            
        try:
            scene = self.scenes[self.active_scene_id]
            current_effect = scene.get_current_effect()
            
            if current_effect:
                led_output = self.get_led_output_with_timing(time.time())
                active_count = sum(1 for color in led_output if any(c > 0 for c in color))
                
                logger.debug(f"Animation frame {self._debug_frame_count}: {active_count}/{len(led_output)} LEDs active")
                
                if self.pattern_transition.is_active:
                    logger.debug(f"Transition: {self.pattern_transition.phase.value}, progress: {self.pattern_transition.progress:.2f}")
                
                segment_info = []
                for seg_id, segment in current_effect.segments.items():
                    segment_info.append(f"S{seg_id}:pos={segment.current_position:.1f},spd={segment.move_speed}")
                
                if segment_info:
                    logger.debug(f"Segments: {', '.join(segment_info)}")
                    
        except Exception as e:
            logger.error(f"Error logging animation status: {e}")
    
    def _log_scene_status(self):
        """Log comprehensive scene status with improved LED count reporting"""
        try:
            logger.info("=== SCENE STATUS ===")
            logger.info(f"Total scenes: {len(self.scenes)} (IDs: {list(self.scenes.keys())})")
            logger.info(f"Active scene: {self.active_scene_id}")
            
            if self.active_scene_id is None:
                logger.warning("No active scene set")
                return
                
            if self.active_scene_id not in self.scenes:
                logger.warning(f"Active scene {self.active_scene_id} not found in loaded scenes")
                return
                
            scene = self.scenes[self.active_scene_id]
            current_effect = scene.get_current_effect()
            
            logger.info(f"Scene {scene.scene_id}:")
            logger.info(f"  LED Count: {scene.led_count}, FPS: {scene.fps}")
            logger.info(f"  Effects: {len(scene.effects)} (IDs: 0-{len(scene.effects)-1})")
            logger.info(f"  Palettes: {len(scene.palettes)} (IDs: 0-{len(scene.palettes)-1})")
            logger.info(f"  Current: Effect {scene.current_effect_id}, Palette {scene.current_palette_id}")
            
            if current_effect:
                logger.info(f"Current Effect {current_effect.effect_id}:")
                logger.info(f"  Segments: {len(current_effect.segments)} (IDs: {list(current_effect.segments.keys())})")
                
                total_expected_leds = 0
                for seg_id, segment in current_effect.segments.items():
                    total_length = sum(segment.length) if segment.length else 0
                    has_color = any(c >= 0 for c in segment.color) if segment.color else False
                    expected_leds = total_length if has_color else 0
                    total_expected_leds += expected_leds
                    
                    brightness = segment.get_brightness_at_time(time.time())
                    logger.info(f"  Segment {seg_id}: length={total_length}, pos={segment.current_position:.1f}, "
                              f"speed={segment.move_speed}, colors={len(segment.color)}, brightness={brightness:.3f}")
                
                logger.info(f"  Expected active LEDs: {total_expected_leds}")
                
                try:
                    led_output = scene.get_led_output_with_timing(time.time())
                    actual_active = sum(1 for color in led_output if any(c > 0 for c in color))
                    logger.info(f"  Actual LED output: {len(led_output)} total, {actual_active} active")
                    
                    if actual_active == 0 and total_expected_leds > 0:
                        logger.warning("  WARNING: Expected LEDs but none are active - check brightness/timing")
                        
                except Exception as e:
                    logger.error(f"  Error getting LED output: {e}")
            else:
                logger.warning(f"  Current effect {scene.current_effect_id} not found in effects list")
                
        except Exception as e:
            logger.error(f"Error logging scene status: {e}")
            
    def get_current_scene_info(self) -> Dict[str, Any]:
        """Get detailed information about current scene"""
        with self._lock:
            if self.active_scene_id is None or self.active_scene_id not in self.scenes:
                return {
                    "scene_id": None,
                    "effect_id": None,
                    "palette_id": None,
                    "led_count": EngineSettings.ANIMATION.led_count,
                    "fps": EngineSettings.ANIMATION.target_fps,
                    "total_scenes": len(self.scenes),
                    "total_effects": 0,
                    "total_segments": 0,
                    "available_scenes": list(self.scenes.keys()),
                    "available_effects": [],
                    "available_palettes": []
                }
            
            scene = self.scenes[self.active_scene_id]
            current_effect = scene.get_current_effect()
            
            return {
                "scene_id": scene.scene_id,
                "effect_id": scene.current_effect_id,
                "palette_id": scene.current_palette_id,
                "led_count": scene.led_count,
                "fps": scene.fps,
                "total_scenes": len(self.scenes),
                "total_effects": len(scene.effects),
                "total_segments": len(current_effect.segments) if current_effect else 0,
                "available_scenes": list(self.scenes.keys()),
                "available_effects": list(range(len(scene.effects))),
                "available_palettes": list(range(len(scene.palettes)))
            }
    
    def get_active_effects_count(self) -> int:
        """Get number of active effects for FPS balancer"""
        try:
            with self._lock:
                if self.active_scene_id is None or self.active_scene_id not in self.scenes:
                    return 0
                
                return len(self.scenes[self.active_scene_id].effects)
                
        except Exception as e:
            logger.error(f"Error getting active effects count: {e}")
            return 0
    
    def switch_scene(self, scene_id: int, use_dissolve: bool = False) -> bool:
        """Switch to a different scene using zero-origin ID"""
        try:
            with self._lock:
                if scene_id not in self.scenes:
                    available_scenes = list(self.scenes.keys())
                    logger.warning(f"Scene {scene_id} not found. Available: {available_scenes}")
                    return False
                
                if use_dissolve and self.dissolve_patterns:
                    success = self.start_dissolve_transition(to_scene_id=scene_id)
                    if success:
                        self.stats['scene_switches'] += 1
                        return True
                
                old_scene_id = self.active_scene_id
                self.active_scene_id = scene_id
                
                self.stats['scene_switches'] += 1
                self._notify_changes()
                
                logger.operation("switch_scene", f"Scene {old_scene_id}→{scene_id}")
                self._log_scene_status()
                return True
                
        except Exception as e:
            logger.error(f"Error switching scene: {e}")
            self.stats['errors'] += 1
            return False
    
    def get_dissolve_info(self) -> Dict[str, Any]:
        """Get dissolve system information"""
        with self._lock:
            return {
                "enabled": len(self.dissolve_patterns) > 0,
                "current_pattern_id": self.current_dissolve_pattern_id,
                "available_patterns": list(self.dissolve_patterns.keys()),
                "pattern_count": len(self.dissolve_patterns),
                "transition_active": self.dissolve_transition.is_active,
                "transition_phase": self.dissolve_transition.phase.value if self.dissolve_transition.is_active else "completed"
            }