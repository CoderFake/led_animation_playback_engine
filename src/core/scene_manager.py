"""
SceneManager implementation with dual pattern dissolve crossfade support
Handles scene/effect/palette changes with simultaneous animation of old and new patterns
"""

import json
import time
import threading
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any

from ..models.scene import Scene
from ..models.common import DissolveTransition, DualPatternCalculator, PatternState
from ..models.types import DissolvePhase
from ..utils.logging import LoggingUtils
from ..utils.dissolve_pattern import DissolvePatternManager
from config.settings import EngineSettings


logger = LoggingUtils._get_logger("SceneManager")


class SceneManager:
    """
    Scene management with dual pattern dissolve crossfade transitions
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
        
        self.stats = {
            'scenes_loaded': 0,
            'scene_switches': 0,
            'effect_changes': 0,
            'palette_changes': 0,
            'dissolve_transitions_completed': 0,
            'errors': 0
        }
        
        logger.info("SceneManager initialized with dual pattern dissolve system")
        logger.info("Dissolve crossfade system ready")
    
    async def initialize(self):
        """Initialize the scene manager"""
        logger.info("Initializing Scene Manager...")
        logger.info("Scene Manager initialization complete")
        logger.info("Ready to receive OSC commands")
    
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
                
                scenes_loaded = 0
                
                for scene_data in scenes_data:
                    try:
                        scene = Scene.from_dict(scene_data)
                        self.scenes[scene.scene_id] = scene
                        scenes_loaded += 1
                        logger.debug(f"Loaded scene {scene.scene_id}")
                    except Exception as e:
                        logger.error(f"Error loading scene: {e}")
                        continue
                
                if scenes_loaded > 0:
                    if self.current_scene_id is None:
                        first_scene_id = min(self.scenes.keys())
                        self.current_scene_id = first_scene_id
                        self.current_scene = self.scenes[first_scene_id]
                    
                    self.stats['scenes_loaded'] += scenes_loaded
                    logger.info(f"Loaded {scenes_loaded} scenes from {file_path}")
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
            logger.info(f"Active scene: {self.current_scene_id} "
                       f"(Effect: {self.current_scene.current_effect_id}, "
                       f"Palette: {self.current_scene.current_palette_id})")
    
    # ==================== Animation Update ====================
    
    def update_animation(self, delta_time: float):
        """Update animation for current scene and dissolve transitions"""
        try:
            with self._lock:
                if not self.current_scene:
                    return
                
                # Update current scene animation
                current_effect = self.current_scene.get_current_effect()
                if current_effect:
                    current_effect.update_animation(delta_time)
                
                # Update any other scenes involved in dissolve transition
                if self.dissolve_transition.is_active:
                    if (self.dissolve_transition.old_pattern and 
                        self.dissolve_transition.old_pattern.scene_id in self.scenes):
                        old_scene = self.scenes[self.dissolve_transition.old_pattern.scene_id]
                        if self.dissolve_transition.old_pattern.effect_id < len(old_scene.effects):
                            old_effect = old_scene.effects[self.dissolve_transition.old_pattern.effect_id]
                            old_effect.update_animation(delta_time)
                    
                    if (self.dissolve_transition.new_pattern and 
                        self.dissolve_transition.new_pattern.scene_id in self.scenes):
                        new_scene = self.scenes[self.dissolve_transition.new_pattern.scene_id]
                        if self.dissolve_transition.new_pattern.effect_id < len(new_scene.effects):
                            new_effect = new_scene.effects[self.dissolve_transition.new_pattern.effect_id]
                            new_effect.update_animation(delta_time)
                    
        except Exception as e:
            logger.error(f"Error updating animation: {e}")
    
    # ==================== LED Output Methods ====================
    
    def get_rendered_led_array(self) -> List[List[int]]:
        """Get final rendered LED array with dual pattern dissolve crossfade"""
        try:
            if self.dissolve_transition.is_active:
                result = self.dissolve_transition.update_dissolve(time.time())
                
                if not self.dissolve_transition.is_active:
                    self.stats['dissolve_transitions_completed'] += 1
                    logger.info("Dual pattern dissolve transition completed")
                
                return result
            else:
                return self._get_current_led_array()
                
        except Exception as e:
            logger.error(f"Error getting rendered LED array: {e}")
            return [[0, 0, 0] for _ in range(225)]
    
    def get_led_output_with_timing(self, current_time: float) -> List[List[int]]:
        """Get LED output with time-based brightness and dual pattern crossfade"""
        try:
            with self._lock:
                if not self.current_scene:
                    return [[0, 0, 0] for _ in range(EngineSettings.ANIMATION.led_count)]
                
                # Check if dissolve is active
                if self.dissolve_transition.is_active:
                    return self.dissolve_transition.update_dissolve(current_time)
                
                # Normal rendering when no dissolve
                current_effect = self.current_scene.get_current_effect()
                if not current_effect:
                    return [[0, 0, 0] for _ in range(self.current_scene.led_count)]
                
                led_array = [[0, 0, 0] for _ in range(self.current_scene.led_count)]
                palette = self.current_scene.get_current_palette()
                
                current_effect.render_to_led_array(palette, current_time, led_array)
                
                return led_array
                
        except Exception as e:
            logger.error(f"Error getting LED output with timing: {e}")
            return [[0, 0, 0] for _ in range(225)]
    
    def _get_current_led_array(self) -> List[List[int]]:
        """Get current LED array state for single pattern rendering"""
        if not self.current_scene:
            return [[0, 0, 0] for _ in range(225)]
        
        led_array = [[0, 0, 0] for _ in range(self.current_scene.led_count)]
        current_effect = self.current_scene.get_current_effect()
        
        if current_effect:
            palette = self.current_scene.get_current_palette()
            current_effect.render_to_led_array(palette, time.time(), led_array)
        
        return led_array
    
    # ==================== Dissolve Pattern Management ====================
    
    def load_dissolve_json(self, file_path: str) -> bool:
        """Load dissolve patterns from JSON file"""
        try:
            if not file_path.endswith('.json'):
                file_path += '.json'
            
            success = self.dissolve_patterns.load_patterns_from_json(file_path)
            if success:
                logger.info(f"Loaded dissolve patterns from {file_path}")
                pattern_ids = self.dissolve_patterns.get_available_patterns()
                logger.info(f"Available dissolve patterns: {pattern_ids}")
                
                if self.dissolve_patterns.current_pattern_id is None and pattern_ids:
                    self.dissolve_patterns.set_current_pattern(pattern_ids[0])
                    logger.info(f"Auto-set dissolve pattern to {pattern_ids[0]}")
            else:
                logger.error(f"Failed to load dissolve patterns from {file_path}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error loading dissolve JSON: {e}")
            return False
    
    def set_dissolve_pattern(self, pattern_id: int) -> bool:
        """Set current dissolve pattern"""
        try:
            success = self.dissolve_patterns.set_current_pattern(pattern_id)
            if success:
                logger.info(f"Dissolve pattern set to {pattern_id}")
            else:
                available = self.dissolve_patterns.get_available_patterns()
                logger.warning(f"Dissolve pattern {pattern_id} not found. Available: {available}")
            
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
    
    def _start_dual_dissolve_if_enabled(self, old_pattern: PatternState, new_pattern: PatternState):
        """Start dual pattern dissolve if pattern is set"""
        if self.dissolve_patterns.current_pattern_id is not None:
            pattern = self.dissolve_patterns.get_pattern(self.dissolve_patterns.current_pattern_id)
            if pattern:
                led_count = self.current_scene.led_count if self.current_scene else 225
                self.dissolve_transition.start_dissolve(
                    old_pattern,
                    new_pattern,
                    pattern,
                    led_count
                )
    
    # ==================== Scene Operations ====================
    
    def change_scene(self, scene_id: int) -> bool:
        """Change scene with dual pattern dissolve crossfade if pattern is set"""
        try:
            with self._lock:
                if scene_id not in self.scenes:
                    available_scenes = list(self.scenes.keys())
                    logger.warning(f"Scene {scene_id} not found. Available: {available_scenes}")
                    return False
                
                old_pattern = self._create_current_pattern_state()
                old_scene_id = self.current_scene_id
                
                self.current_scene_id = scene_id
                self.current_scene = self.scenes[scene_id]
                
                new_pattern = self._create_current_pattern_state()
                
                if old_pattern and new_pattern:
                    self._start_dual_dissolve_if_enabled(old_pattern, new_pattern)
                    if self.dissolve_transition.is_active:
                        logger.info(f"Scene {old_scene_id}→{scene_id} with dual pattern dissolve")
                    else:
                        logger.info(f"Scene {old_scene_id}→{scene_id} (direct)")
                else:
                    logger.info(f"Scene change to {scene_id} (direct)")
                
                self.stats['scene_switches'] += 1
                self._log_scene_status()
                self._notify_changes()
                return True
                
        except Exception as e:
            logger.error(f"Error changing scene: {e}")
            self.stats['errors'] += 1
            return False
    
    def change_effect(self, effect_id: int) -> bool:
        """Change effect with dual pattern dissolve crossfade if pattern is set"""
        try:
            with self._lock:
                if not self.current_scene:
                    logger.warning("No active scene for effect change")
                    return False
                
                available_effects = list(range(len(self.current_scene.effects)))
                if effect_id < 0 or effect_id >= len(self.current_scene.effects):
                    logger.warning(f"Effect ID {effect_id} invalid. Available effects: {available_effects}")
                    return False
                
                old_pattern = self._create_current_pattern_state()
                old_effect_id = self.current_scene.current_effect_id
                
                self.current_scene.current_effect_id = effect_id
                
                new_pattern = self._create_current_pattern_state()
                
                if old_pattern and new_pattern:
                    self._start_dual_dissolve_if_enabled(old_pattern, new_pattern)
                    if self.dissolve_transition.is_active:
                        logger.info(f"Effect {old_effect_id}→{effect_id} with dual pattern dissolve")
                    else:
                        logger.info(f"Effect {old_effect_id}→{effect_id} (direct)")
                else:
                    logger.info(f"Effect change to {effect_id} (direct)")
                
                self.stats['effect_changes'] += 1
                self._log_scene_status()
                self._notify_changes()
                return True
                
        except Exception as e:
            logger.error(f"Error changing effect: {e}")
            self.stats['errors'] += 1
            return False
    
    def change_palette(self, palette_id: int) -> bool:
        """Change palette with dual pattern dissolve crossfade if pattern is set"""
        try:
            with self._lock:
                if not self.current_scene:
                    logger.warning("No active scene for palette change")
                    return False
                
                if palette_id >= len(self.current_scene.palettes):
                    logger.warning(f"Palette {palette_id} not found. Available: 0-{len(self.current_scene.palettes)-1}")
                    return False
                
                old_pattern = self._create_current_pattern_state()
                old_palette_id = self.current_scene.current_palette_id
                self.current_scene.current_palette_id = palette_id
                
                new_pattern = self._create_current_pattern_state()
                
                if old_pattern and new_pattern:
                    self._start_dual_dissolve_if_enabled(old_pattern, new_pattern)
                    if self.dissolve_transition.is_active:
                        logger.info(f"Palette {old_palette_id}→{palette_id} with dual pattern dissolve")
                    else:
                        logger.info(f"Palette {old_palette_id}→{palette_id} (direct)")
                else:
                    logger.info(f"Palette change to {palette_id} (direct)")
                
                self.stats['palette_changes'] += 1
                self._log_scene_status()
                self._notify_changes()
                return True
                
        except Exception as e:
            logger.error(f"Error changing palette: {e}")
            self.stats['errors'] += 1
            return False
    
    def update_palette_color(self, palette_id: int, color_id: int, r: int, g: int, b: int) -> bool:
        """Update a color in the current scene's palette"""
        try:
            with self._lock:
                if not self.current_scene:
                    logger.warning("No active scene for palette color update")
                    return False
                
                if palette_id >= len(self.current_scene.palettes):
                    logger.warning(f"Palette {palette_id} not found")
                    return False
                
                if color_id >= len(self.current_scene.palettes[palette_id]):
                    logger.warning(f"Color {color_id} not found in palette {palette_id}")
                    return False
                
                r = max(0, min(255, int(r)))
                g = max(0, min(255, int(g)))
                b = max(0, min(255, int(b)))
                
                self.current_scene.palettes[palette_id][color_id] = [r, g, b]
                
                logger.info(f"Palette {palette_id}[{color_id}] = RGB({r},{g},{b})")
                self._notify_changes()
                return True
                
        except Exception as e:
            logger.error(f"Error updating palette color: {e}")
            self.stats['errors'] += 1
            return False
    
    # ==================== Status and Information ====================
    
    def get_scene_info(self) -> Dict[str, Any]:
        """Get current scene information"""
        with self._lock:
            if not self.current_scene:
                return {
                    "error": "No active scene",
                    "available_scenes": list(self.scenes.keys())
                }
            
            available_effects = []
            if hasattr(self.current_scene, 'effects'):
                available_effects = list(range(len(self.current_scene.effects)))
            
            return {
                "scene_id": self.current_scene_id,
                "effect_id": self.current_scene.current_effect_id,
                "palette_id": self.current_scene.current_palette_id,
                "led_count": self.current_scene.led_count,
                "fps": self.current_scene.fps,
                "available_effects": available_effects,
                "available_palettes": list(range(len(self.current_scene.palettes))),
                "available_scenes": list(self.scenes.keys()),
                "dissolve_info": self.get_dissolve_info()
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get scene manager statistics"""
        with self._lock:
            return self.stats.copy()
    
    def get_available_scenes(self) -> List[int]:
        """Get list of available scene IDs"""
        with self._lock:
            return list(self.scenes.keys())
    
    def is_scene_loaded(self, scene_id: int) -> bool:
        """Check if a scene is loaded"""
        with self._lock:
            return scene_id in self.scenes
    
    def reset_stats(self):
        """Reset statistics"""
        with self._lock:
            for key in self.stats:
                self.stats[key] = 0
            logger.info("Statistics reset")
    
    def get_current_scene_led_count(self) -> int:
        """Get LED count of current scene"""
        with self._lock:
            if self.current_scene:
                return self.current_scene.led_count
            return 225
    
    def force_stop_dissolve(self):
        """Force stop current dissolve transition"""
        with self._lock:
            if self.dissolve_transition.is_active:
                self.dissolve_transition.is_active = False
                self.dissolve_transition.phase = DissolvePhase.COMPLETED
                logger.info("Dual pattern dissolve transition force stopped")
    
    def shutdown(self):
        """Shutdown the scene manager"""
        with self._lock:
            self.dissolve_transition.is_active = False
            
            self._change_callbacks.clear()
            
            logger.info("SceneManager shutdown complete")