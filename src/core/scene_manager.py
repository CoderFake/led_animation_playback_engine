"""
Scene Manager - Terminal Optimized
Handles scene loading, management, and pattern transitions
Optimized for background operation with comprehensive error handling
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

logger = ComponentLogger("SceneManager")


class TransitionPhase(Enum):
    """Pattern transition phases"""
    FADE_OUT = "fade_out"
    WAITING = "waiting" 
    FADE_IN = "fade_in"
    COMPLETED = "completed"


@dataclass
class PatternTransitionConfig:
    """Configuration for pattern transitions"""
    fade_in_ms: int = 100
    fade_out_ms: int = 100
    waiting_ms: int = 50


@dataclass  
class PatternTransition:
    """Active pattern transition state"""
    is_active: bool = False
    phase: TransitionPhase = TransitionPhase.COMPLETED
    
    from_effect_id: int = None
    from_palette_id: str = None
    to_effect_id: int = None
    to_palette_id: str = None
    
    start_time: float = 0.0
    fade_in_ms: int = 100
    fade_out_ms: int = 100
    waiting_ms: int = 50
    
    phase_start_time: float = 0.0
    progress: float = 0.0


class SceneManager:
    """
    Manages animation scenes, effects, and pattern transitions
    Optimized for terminal operation with comprehensive monitoring
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
        
        self.stats = {
            'scenes_loaded': 0,
            'scene_switches': 0,
            'effect_changes': 0,
            'palette_changes': 0,
            'transitions_completed': 0,
            'errors': 0
        }
        
        logger.info("SceneManager initialized")
        logger.info(f"Pattern transitions: {'enabled' if EngineSettings.PATTERN_TRANSITION.enabled else 'disabled'}")
    
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
        """Notify all registered callbacks of changes"""
        for callback in self._change_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"Error in change callback: {e}")
                self.stats['errors'] += 1
    
    def set_transition_config(self, fade_in_ms: int = None, fade_out_ms: int = None, waiting_ms: int = None):
        """Configure pattern transition timing"""
        with self._lock:
            if fade_in_ms is not None:
                self.transition_config.fade_in_ms = max(0, fade_in_ms)
            if fade_out_ms is not None:
                self.transition_config.fade_out_ms = max(0, fade_out_ms)
            if waiting_ms is not None:
                self.transition_config.waiting_ms = max(0, waiting_ms)
        
        logger.operation("transition_config", 
                        f"fade_in={self.transition_config.fade_in_ms}ms, "
                        f"fade_out={self.transition_config.fade_out_ms}ms, "
                        f"waiting={self.transition_config.waiting_ms}ms")
    
    def start_pattern_transition(self, to_effect_id: int = None, to_palette_id: str = None):
        """Start a pattern transition between effects/palettes"""
        with self._lock:
            if not self.active_scene_id or self.active_scene_id not in self.scenes:
                logger.warning("Cannot start transition: no active scene")
                return False
            
            current_scene = self.scenes[self.active_scene_id]
            
            self.pattern_transition.is_active = True
            self.pattern_transition.phase = TransitionPhase.FADE_OUT
            
            self.pattern_transition.from_effect_id = current_scene.current_effect_id
            self.pattern_transition.from_palette_id = current_scene.current_palette
            self.pattern_transition.to_effect_id = to_effect_id or current_scene.current_effect_id
            self.pattern_transition.to_palette_id = to_palette_id or current_scene.current_palette
            
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
        """Update active pattern transition state"""
        if not self.pattern_transition.is_active:
            return
            
        phase_elapsed = (current_time - self.pattern_transition.phase_start_time) * 1000
        
        if self.pattern_transition.phase == TransitionPhase.FADE_OUT:
            if phase_elapsed >= self.pattern_transition.fade_out_ms:
                self.pattern_transition.phase = TransitionPhase.WAITING
                self.pattern_transition.phase_start_time = current_time
                logger.debug("Transition: FADE_OUT → WAITING")
            else:
                self.pattern_transition.progress = 1.0 - (phase_elapsed / self.pattern_transition.fade_out_ms)
        
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
                self.pattern_transition.progress = phase_elapsed / self.pattern_transition.fade_in_ms
    
    def _complete_pattern_transition(self):
        """Complete the active pattern transition"""
        if not self.active_scene_id or self.active_scene_id not in self.scenes:
            return
            
        scene = self.scenes[self.active_scene_id]
        scene.current_effect_id = self.pattern_transition.to_effect_id
        scene.current_palette = self.pattern_transition.to_palette_id
        
        self.pattern_transition.is_active = False
        self.pattern_transition.phase = TransitionPhase.COMPLETED
        
        self.stats['transitions_completed'] += 1
        
        logger.operation("pattern_transition_complete", 
                        f"Effect {self.pattern_transition.to_effect_id}, "
                        f"Palette {self.pattern_transition.to_palette_id}")
        self._notify_changes()
    
    def get_led_output(self) -> List[List[int]]:
        """Get current LED output with transition handling"""
        with self._lock:
            if not self.pattern_transition.is_active:
                if self.active_scene_id and self.active_scene_id in self.scenes:
                    scene = self.scenes[self.active_scene_id]
                    return scene.get_led_output()
                return [[0, 0, 0] for _ in range(EngineSettings.ANIMATION.led_count)]
            
            return self._get_transition_led_output()
    
    def _get_transition_led_output(self) -> List[List[int]]:
        """Generate LED output during transitions"""
        if not self.active_scene_id or self.active_scene_id not in self.scenes:
            return [[0, 0, 0] for _ in range(EngineSettings.ANIMATION.led_count)]
        
        scene = self.scenes[self.active_scene_id]
        
        if self.pattern_transition.phase == TransitionPhase.FADE_OUT:
            scene.current_effect_id = self.pattern_transition.from_effect_id
            scene.current_palette = self.pattern_transition.from_palette_id
            output = scene.get_led_output()
            
            brightness = self.pattern_transition.progress
            return [
                [int(color[0] * brightness), int(color[1] * brightness), int(color[2] * brightness)]
                for color in output
            ]
        
        elif self.pattern_transition.phase == TransitionPhase.WAITING:
            return [[0, 0, 0] for _ in range(EngineSettings.ANIMATION.led_count)]
        
        elif self.pattern_transition.phase == TransitionPhase.FADE_IN:
            scene.current_effect_id = self.pattern_transition.to_effect_id
            scene.current_palette = self.pattern_transition.to_palette_id
            output = scene.get_led_output()
            
            brightness = self.pattern_transition.progress
            return [
                [int(color[0] * brightness), int(color[1] * brightness), int(color[2] * brightness)]
                for color in output
            ]
        
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
                
                if "scene_ID" in data:
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
                    logger.warning(f"File {file_path} missing scene_ID - not a valid single scene format")
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
                        if "scene_ID" not in scene_data:
                            logger.warning(f"Scene data missing scene_ID: {scene_data}")
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
    
    def load_scene(self, scene_data: Dict[str, Any]) -> bool:
        """Load scene from dictionary data"""
        try:
            with self._lock:
                scene = Scene.from_dict(scene_data)
                self.scenes[scene.scene_id] = scene
                
                if self.active_scene_id is None:
                    self.active_scene_id = scene.scene_id
                
                self.stats['scenes_loaded'] += 1
                self._notify_changes()
                logger.operation("load_scene", f"Scene {scene.scene_id} loaded from data")
                return True
                
        except Exception as e:
            logger.error(f"Error loading scene from data: {e}")
            self.stats['errors'] += 1
            return False
    
    def switch_scene(self, scene_id: int, fade_params: List[int] = None) -> bool:
        """Switch to a different scene"""
        try:
            with self._lock:
                if scene_id not in self.scenes:
                    available_scenes = list(self.scenes.keys())
                    logger.warning(f"Scene {scene_id} not found. Available: {available_scenes}")
                    return False
                    
                old_scene_id = self.active_scene_id
                self.active_scene_id = scene_id
                
                if fade_params:
                    self.scenes[scene_id].fade_params = fade_params
                
                self.stats['scene_switches'] += 1
                self._notify_changes()
                
                logger.operation("switch_scene", f"Scene {old_scene_id}→{scene_id}")
                self._log_scene_status()
                return True
                
        except Exception as e:
            logger.error(f"Error switching scene: {e}")
            self.stats['errors'] += 1
            return False
    
    def set_effect_palette(self, scene_id: int, effect_id: int, palette_id: str) -> bool:
        """Set effect and palette for specific scene"""
        try:
            with self._lock:
                if scene_id not in self.scenes:
                    logger.warning(f"Scene {scene_id} does not exist")
                    return False
                    
                scene = self.scenes[scene_id]
                scene.switch_effect(effect_id, palette_id)
                
                self.stats['effect_changes'] += 1
                self.stats['palette_changes'] += 1
                self._notify_changes()
                
                logger.operation("set_effect_palette", f"Scene {scene_id}: effect {effect_id}, palette {palette_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error setting effect/palette: {e}")
            self.stats['errors'] += 1
            return False
    
    def set_effect(self, effect_id: int) -> bool:
        """Set effect for active scene"""
        try:
            with self._lock:
                if not self.active_scene_id or self.active_scene_id not in self.scenes:
                    logger.warning("No active scene for effect change")
                    return False
                
                scene = self.scenes[self.active_scene_id]
                if str(effect_id) not in scene.effects:
                    available_effects = list(scene.effects.keys())
                    logger.warning(f"Effect {effect_id} not found in scene {self.active_scene_id}. Available: {available_effects}")
                    return False
                
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
    
    def set_palette(self, palette_id: str) -> bool:
        """Set palette for active scene"""
        try:
            with self._lock:
                if not self.active_scene_id or self.active_scene_id not in self.scenes:
                    logger.warning("No active scene for palette change")
                    return False
                
                scene = self.scenes[self.active_scene_id]
                if palette_id not in scene.palettes:
                    available_palettes = list(scene.palettes.keys())
                    logger.warning(f"Palette {palette_id} not found in scene {self.active_scene_id}. Available: {available_palettes}")
                    return False
                
                if EngineSettings.PATTERN_TRANSITION.enabled:
                    success = self.start_pattern_transition(to_palette_id=palette_id)
                    if success:
                        self.stats['palette_changes'] += 1
                    return success
                else:
                    scene.current_palette = palette_id
                    self.stats['palette_changes'] += 1
                    logger.operation("set_palette", f"Palette {palette_id} for scene {self.active_scene_id}")
                    self._notify_changes()
                    return True
                
        except Exception as e:
            logger.error(f"Error setting palette: {e}")
            self.stats['errors'] += 1
            return False
    
    def set_move_speed(self, scene_id: int, speed: float) -> bool:
        """Set movement speed for all segments in scene"""
        try:
            with self._lock:
                if scene_id not in self.scenes:
                    logger.warning(f"Scene {scene_id} not found for speed change")
                    return False
                    
                scene = self.scenes[scene_id]
                current_effect = scene.get_current_effect()
                
                if current_effect:
                    segments_updated = 0
                    for segment in current_effect.segments.values():
                        old_speed = segment.move_speed
                        segment.move_speed = speed if segment.move_speed >= 0 else -speed
                        segments_updated += 1
                    
                    logger.operation("set_move_speed", f"Updated {segments_updated} segments in scene {scene_id} to speed {speed}")
                    self._notify_changes()
                    return True
                else:
                    logger.warning(f"No current effect in scene {scene_id} for speed change")
                    return False
                    
        except Exception as e:
            logger.error(f"Error setting move speed: {e}")
            self.stats['errors'] += 1
            return False
    
    def update_palette_color(self, palette_id: str, color_id: int, rgb: List[int]) -> bool:
        """Update specific color in palette"""
        try:
            with self._lock:
                if not self.active_scene_id or self.active_scene_id not in self.scenes:
                    logger.warning("No active scene for palette color update")
                    return False
                
                scene = self.scenes[self.active_scene_id]
                if palette_id not in scene.palettes:
                    logger.warning(f"Palette {palette_id} not found in active scene")
                    return False
                
                if 0 <= color_id < len(scene.palettes[palette_id]):
                    old_color = scene.palettes[palette_id][color_id].copy()
                    scene.palettes[palette_id][color_id] = rgb[:3]
                    
                    logger.operation("update_palette_color", 
                                   f"Palette {palette_id}[{color_id}]: {old_color}→{rgb[:3]}")
                    self._notify_changes()
                    return True
                else:
                    logger.warning(f"Color index {color_id} out of range for palette {palette_id}")
                    return False
                
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
                for effect in scene.effects.values():
                    effect.update_animation(delta_time)
    
    def _log_animation_status(self):
        """Log animation status for debugging"""
        if not self.active_scene_id or self.active_scene_id not in self.scenes:
            return
            
        try:
            scene = self.scenes[self.active_scene_id]
            current_effect = scene.get_current_effect()
            
            if current_effect:
                led_output = self.get_led_output()
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
        """Log comprehensive scene status"""
        try:
            logger.info("=== SCENE STATUS ===")
            logger.info(f"Total scenes: {len(self.scenes)} (IDs: {list(self.scenes.keys())})")
            logger.info(f"Active scene: {self.active_scene_id}")
            
            if not self.active_scene_id or self.active_scene_id not in self.scenes:
                logger.warning("No active scene or active scene not found")
                return
                
            scene = self.scenes[self.active_scene_id]
            current_effect = scene.get_current_effect()
            
            logger.info(f"Scene {scene.scene_id}:")
            logger.info(f"  Effects: {len(scene.effects)} (IDs: {list(scene.effects.keys())})")
            logger.info(f"  Palettes: {len(scene.palettes)} (IDs: {list(scene.palettes.keys())})")
            logger.info(f"  Current: Effect {scene.current_effect_id}, Palette {scene.current_palette}")
            
            if current_effect:
                logger.info(f"Current Effect {current_effect.effect_id}:")
                logger.info(f"  LED Count: {current_effect.led_count}")
                logger.info(f"  FPS: {current_effect.fps}")
                logger.info(f"  Segments: {len(current_effect.segments)} (IDs: {list(current_effect.segments.keys())})")
                
                total_expected_leds = 0
                for seg_id, segment in current_effect.segments.items():
                    total_length = sum(segment.length) if segment.length else 0
                    has_color = any(c > 0 for c in segment.color) if segment.color else False
                    expected_leds = total_length if has_color else 0
                    total_expected_leds += expected_leds
                    
                    logger.info(f"  Segment {seg_id}: length={total_length}, pos={segment.current_position:.1f}, "
                              f"speed={segment.move_speed}, colors={len(segment.color)}")
                
                logger.info(f"  Expected active LEDs: {total_expected_leds}")
                
                try:
                    led_output = scene.get_led_output()
                    actual_active = sum(1 for color in led_output if any(c > 0 for c in color))
                    logger.info(f"  Actual LED output: {len(led_output)} total, {actual_active} active")
                except Exception as e:
                    logger.error(f"  Error getting LED output: {e}")
            else:
                logger.warning(f"  Current effect {scene.current_effect_id} not found")
                
        except Exception as e:
            logger.error(f"Error logging scene status: {e}")
            
    def get_current_scene_info(self) -> Dict[str, Any]:
        """Get detailed information about current scene"""
        with self._lock:
            if not self.active_scene_id or self.active_scene_id not in self.scenes:
                return {
                    "scene_id": None,
                    "effect_id": None,
                    "palette_id": None,
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
                "palette_id": scene.current_palette,
                "total_scenes": len(self.scenes),
                "total_effects": len(scene.effects),
                "total_segments": len(current_effect.segments) if current_effect else 0,
                "available_scenes": list(self.scenes.keys()),
                "available_effects": list(scene.effects.keys()),
                "available_palettes": list(scene.palettes.keys())
            }