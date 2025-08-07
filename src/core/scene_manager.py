"""
SceneManager implementation with pattern dissolve crossfade support
Handles scene/effect/palette changes 
"""

import json
import time
import threading
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any

from ..models.scene import Scene
from ..models.common import DissolveTransition, DualPatternCalculator, PatternState
from ..utils.logging import LoggingUtils
from ..utils.dissolve_pattern import DissolvePatternManager

logger = LoggingUtils._get_logger("SceneManager")


class SceneManager:
    """
    Scene management with pattern dissolve crossfade transitions
    Handles loading, switching, and transitioning between patterns (Effect × Palette combinations)
    """
    
    def __init__(self):
        self.scenes: Dict[int, Scene] = {}
        self.current_scene_id: Optional[int] = None
        self.current_scene: Optional[Scene] = None
        
        self._lock = threading.RLock()
        self._change_callbacks: List[Callable] = []
        
        self.dissolve_patterns = DissolvePatternManager()
        self.dissolve_transition = DissolveTransition()
        self.dual_calculator = DualPatternCalculator(self)
        
        self.dissolve_transition.set_calculator(self.dual_calculator)
    
        self.current_speed_percent = 100
        
        self.original_scene_speeds: Dict[int, Dict[str, Dict[str, float]]] = {}
        
        self.cached_scene_id: Optional[int] = None
        self.cached_effect_id: Optional[int] = None
        self.cached_palette_id: Optional[int] = None
        self.has_pending_changes = False
        self.is_initial = True
        
        self.stats = {
            'scenes_loaded': 0,
            'scene_switches': 0,
            'effect_changes': 0,
            'palette_changes': 0,
            'pattern_changes': 0, 
            'dissolve_transitions_completed': 0,
            'errors': 0
        }
    
    async def initialize(self):
        """Initialize the scene manager"""
        logger.info("Initializing Scene Manager...")
    
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
    
    # ==================== Cache Management ====================
    
    def _cache_current_state(self):
        """Cache current state before changes"""
        with self._lock:
            if self.current_scene:
                self.cached_scene_id = self.current_scene_id
                self.cached_effect_id = self.current_scene.current_effect_id
                self.cached_palette_id = self.current_scene.current_palette_id
            else:
                self.cached_scene_id = 0
                self.cached_effect_id = 0
                self.cached_palette_id = 0
    
    def _has_actual_changes(self) -> bool:
        """Check if there are any actual pattern changes (no logging)"""
        if not self.current_scene or not self.has_pending_changes:
            return False
            
        scene_changed = self.cached_scene_id != self.current_scene_id
        effect_changed = self.cached_effect_id != self.current_scene.current_effect_id
        palette_changed = self.cached_palette_id != self.current_scene.current_palette_id
        
        return scene_changed or effect_changed or palette_changed

    def _has_pattern_changes(self) -> bool:
        """Check if there are any pattern changes in cache (with logging)"""
        with self._lock:
            if not self.current_scene or not self.has_pending_changes:
                return False
                
            scene_changed = self.cached_scene_id != self.current_scene_id
            effect_changed = self.cached_effect_id != self.current_scene.current_effect_id
            palette_changed = self.cached_palette_id != self.current_scene.current_palette_id
            
            logger.info(f"Change detection: scene={scene_changed}, effect={effect_changed}, palette={palette_changed}")
            
            return scene_changed or effect_changed or palette_changed
    
    def _create_cached_pattern_state(self) -> Optional[PatternState]:
        """Create pattern state from cached values"""
        if (self.cached_scene_id is None or 
            self.cached_effect_id is None or 
            self.cached_palette_id is None):
            return None
        
        return PatternState(
            scene_id=self.cached_scene_id,
            effect_id=self.cached_effect_id,
            palette_id=self.cached_palette_id
        )
    
    def _clear_cache(self):
        """Clear the pattern change cache"""
        with self._lock:
            self.cached_scene_id = None
            self.cached_effect_id = None
            self.cached_palette_id = None
            self.has_pending_changes = False
    
    def get_cache_status(self) -> Dict[str, Any]:
        """Get cache system status"""
        with self._lock:
            return {
                "has_pending_changes": self.has_pending_changes,
                "cached_scene_id": self.cached_scene_id,
                "cached_effect_id": self.cached_effect_id,
                "cached_palette_id": self.cached_palette_id,
                "current_scene_id": self.current_scene_id,
                "current_effect_id": self.current_scene.current_effect_id if self.current_scene else None,
                "current_palette_id": self.current_scene.current_palette_id if self.current_scene else None,
                "changes_detected": self.has_pending_changes and self._has_actual_changes(),
                "dissolve_pattern_loaded": self.dissolve_patterns.current_pattern_id is not None
            }
    
    # ==================== New Change Pattern Handler ====================
    
    def change_pattern(self) -> bool:
        """
        Execute cached pattern changes
        Only executes if dissolve pattern is loaded AND changes are pending
        """
        try:
            with self._lock:
                if self.dissolve_patterns.current_pattern_id is None:
                    logger.info("No dissolve pattern loaded - changes applied without transition")
                    if self.has_pending_changes:
                        self._clear_cache()
                        self._notify_changes()
                        self.stats['pattern_changes'] += 1
                        self.is_initial = False
                    return True
                
                if not self.has_pending_changes:
                    return True
                
                if not self._has_pattern_changes():
                    self._clear_cache()
                    return True
                
                old_pattern = self._create_cached_pattern_state()
                if not old_pattern:
                    logger.warning("Cannot create old pattern state from cache")
                    self._clear_cache()
                    return False
                
                new_pattern = self._create_current_pattern_state()
                if not new_pattern:
                    logger.warning("Cannot create current pattern state")
                    self._clear_cache()
                    return False
                
                transition_type = self._determine_transition_type(old_pattern, new_pattern)
                
                self._execute_cached_dissolve(old_pattern, new_pattern, transition_type)
                
                self._clear_cache()
                self._notify_changes()
                self.stats['pattern_changes'] += 1
                self.is_initial = False
                
                logger.info(f"Pattern change executed: {transition_type} transition with dissolve")
                return True
                
        except Exception as e:
            logger.error(f"Error executing pattern change: {e}")
            self.stats['errors'] += 1
            self._clear_cache()
            return False
    
    def _determine_transition_type(self, old_pattern: PatternState, new_pattern: PatternState) -> str:
        """Determine the type of transition based on pattern changes"""
        if old_pattern.scene_id != new_pattern.scene_id:
            return "scene"
        elif old_pattern.effect_id != new_pattern.effect_id:
            return "effect"
        elif old_pattern.palette_id != new_pattern.palette_id:
            return "palette"
        else:
            return "unknown"
    
    def _execute_cached_dissolve(self, old_pattern: PatternState, new_pattern: PatternState, transition_type: str):
        """Execute dissolve transition with cached patterns"""
        if self.dissolve_patterns.current_pattern_id is not None:
            pattern = self.dissolve_patterns.get_pattern(self.dissolve_patterns.current_pattern_id)
            if pattern:
                led_count = self.current_scene.led_count if self.current_scene else 225
                
                if transition_type == "scene":
                    self._restore_original_speeds(new_pattern.scene_id)
                
                self.dissolve_transition.start_dissolve(
                    old_pattern,
                    new_pattern,
                    pattern,
                    led_count
                )
                
                logger.info(f"Dissolve started: {old_pattern.scene_id}.{old_pattern.effect_id}.{old_pattern.palette_id} → {new_pattern.scene_id}.{new_pattern.effect_id}.{new_pattern.palette_id}")
    
    # ==================== MODIFIED Scene Operations (Cache Only) ====================
    
    def change_scene(self, scene_id: int) -> bool:
        """
        MODIFIED: Change scene - NO automatic dissolve trigger
        Only caches change, waits for change_pattern to execute dissolve
        """
        try:
            with self._lock:
                if scene_id not in self.scenes:
                    available_scenes = list(self.scenes.keys())
                    logger.warning(f"Scene {scene_id} not found. Available: {available_scenes}")
                    return False
                
                if not self.has_pending_changes:
                    self._cache_current_state()
                    self.has_pending_changes = True
                
                old_scene_id = self.current_scene_id
                
                self.current_scene_id = scene_id
                self.current_scene = self.scenes[scene_id]
                
                logger.info(f"Scene cached: {old_scene_id}→{scene_id} (waiting for change_pattern)")
                
                self.stats['scene_switches'] += 1
                self._log_scene_status()
                
                return True
                
        except Exception as e:
            logger.error(f"Error caching scene change: {e}")
            self.stats['errors'] += 1
            return False
    
    def change_effect(self, effect_id: int) -> bool:
        """
        Only caches change, waits for change_pattern to execute dissolve
        """
        try:
            with self._lock:
                if not self.current_scene:
                    logger.warning("No active scene for effect change")
                    return False
                
                available_effects = list(range(len(self.current_scene.effects)))
                if effect_id < 0 or effect_id >= len(self.current_scene.effects):
                    logger.warning(f"Effect ID {effect_id} invalid. Available effects: {available_effects}")
                    return False
                
                if not self.has_pending_changes:
                    self._cache_current_state()
                    self.has_pending_changes = True
                
                old_effect_id = self.current_scene.current_effect_id
                
                self.current_scene.current_effect_id = effect_id
                
                logger.info(f"Effect cached: {old_effect_id}→{effect_id}")
                
                self.stats['effect_changes'] += 1
                self._log_scene_status()
                
                return True
                
        except Exception as e:
            logger.error(f"Error caching effect change: {e}")
            self.stats['errors'] += 1
            return False
    
    def change_palette(self, palette_id: int) -> bool:
        """
        MODIFIED: Change palette - NO automatic dissolve trigger
        Only caches change, waits for change_pattern to execute dissolve
        """
        try:
            with self._lock:
                if not self.current_scene:
                    logger.warning("No active scene for palette change")
                    return False
                
                if palette_id >= len(self.current_scene.palettes):
                    available_palettes = list(range(len(self.current_scene.palettes)))
                    logger.warning(f"Palette {palette_id} not found. Available: {available_palettes}")
                    return False
                
                if not self.has_pending_changes:
                    self._cache_current_state()
                    self.has_pending_changes = True
                
                old_palette_id = self.current_scene.current_palette_id
                
                self.current_scene.current_palette_id = palette_id
                
                logger.info(f"Palette cached: {old_palette_id}→{palette_id} (waiting for change_pattern)")
                
                self.stats['palette_changes'] += 1
                self._log_scene_status()
                
                return True
                
        except Exception as e:
            logger.error(f"Error caching palette change: {e}")
            self.stats['errors'] += 1
            return False
    
    # ==================== PRESERVED Methods ====================
    
    def set_speed_percent(self, speed_percent: int):
        """Set current speed percentage and apply to current scene segments"""
        with self._lock:
            old_speed = self.current_speed_percent
            self.current_speed_percent = speed_percent
            
            if self.current_scene:
                self._apply_speed_to_scene(self.current_scene_id, speed_percent)
            
            logger.info(f"Speed changed from {old_speed}% to {speed_percent}%")

    def _store_original_speeds(self, scene_id: int):
        """Store original move speeds for a scene"""
        if scene_id not in self.scenes:
            return
            
        scene = self.scenes[scene_id]
        scene_speeds = {}
        
        for effect in scene.effects:
            effect_speeds = {}
            for segment_id, segment in effect.segments.items():
                effect_speeds[segment_id] = segment.move_speed
            scene_speeds[str(effect.effect_id)] = effect_speeds
        
        self.original_scene_speeds[scene_id] = scene_speeds
    
    def _apply_speed_to_current_effect(self, scene_id: int, speed_percent: int):
        """Apply speed percentage only to current effect (used for effect changes without dissolve)"""
        if scene_id not in self.scenes or scene_id not in self.original_scene_speeds:
            return
            
        scene = self.scenes[scene_id]
        original_speeds = self.original_scene_speeds[scene_id]
        speed_multiplier = speed_percent / 100.0
        
        current_effect = scene.get_current_effect()
        if current_effect:
            effect_id_str = str(current_effect.effect_id)
            if effect_id_str in original_speeds:
                for segment_id, segment in current_effect.segments.items():
                    if segment_id in original_speeds[effect_id_str]:
                        original_speed = original_speeds[effect_id_str][segment_id]
                        segment.move_speed = original_speed * speed_multiplier

    def _apply_speed_to_scene(self, scene_id: int, speed_percent: int):
        """Apply speed percentage to specific scene segments (used for effect/palette changes)"""
        if scene_id not in self.scenes or scene_id not in self.original_scene_speeds:
            return
            
        scene = self.scenes[scene_id]
        original_speeds = self.original_scene_speeds[scene_id]
        speed_multiplier = speed_percent / 100.0
        
        for effect in scene.effects:
            effect_id_str = str(effect.effect_id)
            if effect_id_str in original_speeds:
                for segment_id, segment in effect.segments.items():
                    if segment_id in original_speeds[effect_id_str]:
                        original_speed = original_speeds[effect_id_str][segment_id]
                        segment.move_speed = original_speed * speed_multiplier

    def _restore_original_speeds(self, scene_id: int):
        """Restore original move speeds for a scene (used for scene changes)"""
        if scene_id not in self.scenes or scene_id not in self.original_scene_speeds:
            return
            
        scene = self.scenes[scene_id]
        original_speeds = self.original_scene_speeds[scene_id]
        
        for effect in scene.effects:
            effect_id_str = str(effect.effect_id)
            if effect_id_str in original_speeds:
                for segment_id, segment in effect.segments.items():
                    if segment_id in original_speeds[effect_id_str]:
                        original_speed = original_speeds[effect_id_str][segment_id]
                        segment.move_speed = original_speed

    # ==================== JSON Loading ====================
    
    def load_multiple_scenes_from_file(self, file_path: str) -> bool:
        """Load multiple scenes from JSON file with 'scenes' array"""
        try:
            with self._lock:
                file_path_obj = Path(file_path)
                if not file_path_obj.exists():
                    logger.error(f"Scene file not found: {file_path}")
                    return False
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if "scenes" not in data:
                    logger.error("Invalid JSON format: missing 'scenes' array")
                    return False
                
                scenes_data = data["scenes"]
                if not isinstance(scenes_data, list):
                    logger.error("Invalid JSON format: 'scenes' must be an array")
                    return False
                
                self.original_scene_speeds.clear()
                
                self.is_initial = True
                self.has_pending_changes = False
                self._clear_cache()
                
                scenes_loaded = 0
                
                for scene_data in scenes_data:
                    try:
                        scene = Scene.from_dict(scene_data)
                        self.scenes[scene.scene_id] = scene
                        self._store_original_speeds(scene.scene_id)
                        
                        scenes_loaded += 1
                    except Exception as e:
                        logger.error(f"Error loading scene: {e}")
                        continue
                
                if scenes_loaded > 0:
                    if self.current_scene_id is None:
                        first_scene_id = min(self.scenes.keys())
                        self.current_scene_id = first_scene_id
                        self.current_scene = self.scenes[first_scene_id]
                        
                        self._restore_original_speeds(first_scene_id)
                    
                    self.is_initial = False
                    
                    self.stats['scenes_loaded'] += scenes_loaded
                    logger.info(f"Available scenes: {sorted(self.scenes.keys())}")
                    self._log_scene_status()
                    self._notify_changes()
                    return True
                else:
                    logger.error("No valid scenes found in file")
                    return False
                    
        except Exception as e:
            logger.error(f"Error loading scenes: {e}")
            self.stats['errors'] += 1
            return False
    
    def _log_scene_status(self):
        """Log current scene status"""
        if self.current_scene:
            current_status = f"Scene={self.current_scene_id} Effect={self.current_scene.current_effect_id} Palette={self.current_scene.current_palette_id}"
            
            if self.has_pending_changes:
                cached_status = f"CACHED: Scene={self.cached_scene_id} Effect={self.cached_effect_id} Palette={self.cached_palette_id}"
                logger.info(f"CURRENT: {current_status}")
                logger.info(f"{cached_status} (waiting for change_pattern)")
            else:
                logger.info(f"STATUS: {current_status}")
    
    def get_scene_info(self) -> Dict[str, Any]:
        """Get current scene information"""
        with self._lock:
            if not self.current_scene:
                return {}
            
            return {
                'scene_id': self.current_scene_id,
                'led_count': self.current_scene.led_count,
                'fps': self.current_scene.fps,
                'current_effect_id': self.current_scene.current_effect_id,
                'current_palette_id': self.current_scene.current_palette_id,
                'effects_count': len(self.current_scene.effects),
                'palettes_count': len(self.current_scene.palettes)
            }
    
    # ==================== Animation Update ====================
    
    def update_animation(self, delta_time: float):
        """
        Update animation for current scene and dissolve transitions
        
        Logic:
        - delta_time from animation_engine is already multiplied by speed_percent
        - move_speed in segments is adjusted by speed_percent (current speed) or original (scene change fade in)
        - To avoid double speed application, always pass original delta_time to effects
        - Avoid updating same effect twice during dissolve (for palette changes)
        """
        try:
            with self._lock:
                if not self.current_scene:
                    return
            
                if self.current_speed_percent > 0:
                    original_delta = delta_time / (self.current_speed_percent / 100.0)
                else:
                    original_delta = delta_time  
                
                if self.dissolve_transition.is_active:
                    updated_effects = set() 
                    
                    if (self.dissolve_transition.old_pattern and 
                        self.dissolve_transition.old_pattern.scene_id in self.scenes):
                        old_scene = self.scenes[self.dissolve_transition.old_pattern.scene_id]
                        if self.dissolve_transition.old_pattern.effect_id < len(old_scene.effects):
                            old_effect = old_scene.effects[self.dissolve_transition.old_pattern.effect_id]
                            effect_key = (self.dissolve_transition.old_pattern.scene_id, self.dissolve_transition.old_pattern.effect_id)
                            if effect_key not in updated_effects:
                                old_effect.update_animation(original_delta)
                                updated_effects.add(effect_key)
                    
                    if (self.dissolve_transition.new_pattern and 
                        self.dissolve_transition.new_pattern.scene_id in self.scenes):
                        new_scene = self.scenes[self.dissolve_transition.new_pattern.scene_id]
                        if self.dissolve_transition.new_pattern.effect_id < len(new_scene.effects):
                            new_effect = new_scene.effects[self.dissolve_transition.new_pattern.effect_id]
                            effect_key = (self.dissolve_transition.new_pattern.scene_id, self.dissolve_transition.new_pattern.effect_id)
                            if effect_key not in updated_effects:
                                new_effect.update_animation(original_delta)
                                updated_effects.add(effect_key)
                else:
                    if self.is_initial:
                        pass
                    elif self.has_pending_changes and self.cached_scene_id is not None:
                        scene_id = self.cached_scene_id
                        effect_id = self.cached_effect_id if self.cached_effect_id is not None else 0
                        
                        if scene_id in self.scenes:
                            cached_scene = self.scenes[scene_id]
                            if effect_id < len(cached_scene.effects):
                                cached_scene.effects[effect_id].update_animation(original_delta)
                    else:
                        if self.current_scene.current_effect_id < len(self.current_scene.effects):
                            current_effect = self.current_scene.effects[self.current_scene.current_effect_id]
                            current_effect.update_animation(original_delta)
                        
        except Exception as e:
            logger.error(f"Error updating effects animation: {e}")
    
    def get_current_led_data(self, led_count: int) -> List[List[int]]:
        """Get current LED data for rendering - FIXED: Use cached values when changes are pending"""
        try:
            with self._lock:
                if not self.current_scene:
                    return [[0, 0, 0] for _ in range(led_count)]
                
                current_time = time.time()
                
                if self.dissolve_transition.is_active:
                    return self.dissolve_transition.update_dissolve(current_time)
                else:
                    led_array = [[0, 0, 0] for _ in range(led_count)]
                    
                    if self.is_initial:
                        pass
                    elif self.has_pending_changes and self.cached_scene_id is not None:
                        scene_id = self.cached_scene_id
                        effect_id = self.cached_effect_id if self.cached_effect_id is not None else 0
                        palette_id = self.cached_palette_id if self.cached_palette_id is not None else 0
                       
                        if scene_id in self.scenes:
                            cached_scene = self.scenes[scene_id]
                            if effect_id < len(cached_scene.effects):
                                effect = cached_scene.effects[effect_id]
                                
                                if palette_id < len(cached_scene.palettes):
                                    palette = cached_scene.palettes[palette_id]
                                else:
                                    palette = [[255, 255, 255]] * 6
                                
                                effect.render_to_led_array(palette, current_time, led_array)
                    else:
                        if self.current_scene.current_effect_id < len(self.current_scene.effects):
                            effect = self.current_scene.effects[self.current_scene.current_effect_id]
                            
                            if self.current_scene.current_palette_id < len(self.current_scene.palettes):
                                palette = self.current_scene.palettes[self.current_scene.current_palette_id]
                            else:
                                palette = [[255, 255, 255]] * 6 
                            
                            effect.render_to_led_array(palette, current_time, led_array)
                    
                    return led_array
                    
        except Exception as e:
            logger.error(f"Error getting LED data: {e}")
            return [[0, 0, 0] for _ in range(led_count)]
    
    # ==================== Dissolve Pattern Management ====================
    
    def load_dissolve_patterns_from_file(self, file_path: str) -> bool:
        """Load dissolve patterns from JSON file"""
        try:
            return self.dissolve_patterns.load_patterns_from_json(file_path)
        except Exception as e:
            logger.error(f"Error loading dissolve patterns: {e}")
            return False
    
    def set_dissolve_pattern(self, pattern_id: int) -> bool:
        """Set current dissolve pattern"""
        try:
            available_patterns = self.dissolve_patterns.get_available_patterns()
            
            if pattern_id not in available_patterns:
                logger.warning(f"Dissolve pattern {pattern_id} not found. Available: {available_patterns}")
                return False
            
            success = self.dissolve_patterns.set_current_pattern(pattern_id)
            
            if success:
                logger.info(f"Dissolve pattern set to {pattern_id}")
            else:
                logger.warning(f"Failed to set dissolve pattern {pattern_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error setting dissolve pattern: {e}")
            return False
    
    def get_dissolve_info(self) -> Dict[str, Any]:
        """Get dissolve system information"""
        with self._lock:
            available_patterns = self.dissolve_patterns.get_available_patterns()
            return {
                "enabled": len(available_patterns) > 0,
                "current_pattern_id": self.dissolve_patterns.current_pattern_id,
                "available_patterns": available_patterns,
                "pattern_count": len(available_patterns),
                "transition_active": self.dissolve_transition.is_active,
                "transition_phase": self.dissolve_transition.phase.value if self.dissolve_transition.is_active else "completed"
            }
    
    # ==================== Pattern Creation ====================
    
    def _create_current_pattern_state(self) -> Optional[PatternState]:
        """Create pattern state for current scene configuration"""
        if not self.current_scene:
            return None
        
        return PatternState(
            scene_id=self.current_scene_id,
            effect_id=self.current_scene.current_effect_id,
            palette_id=self.current_scene.current_palette_id
        )