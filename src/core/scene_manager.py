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
    Scene management with pattern-based dissolve transitions
    Supports parameter-only changes and smart dissolve triggering
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
            'pattern_changes': 0,
            'dissolve_transitions_completed': 0,
            'fade_in_transitions': 0,
            'crossfade_transitions': 0,
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
                
                self.scenes.clear()
                self.current_scene_id = None
                self.current_scene = None
                
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
                    self.stats['scenes_loaded'] += scenes_loaded
                    logger.info(f"Available scenes: {sorted(self.scenes.keys())}")
                    logger.info("Scenes loaded. Use /change_pattern to activate.")
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
                
                current_effect = self.current_scene.get_current_effect()
                if current_effect:
                    current_effect.update_animation(delta_time)
                
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
        """Get final rendered LED array with dissolve crossfade"""
        try:
            if self.dissolve_transition.is_active:
                result = self.dissolve_transition.update_dissolve(time.time())
                
                if not self.dissolve_transition.is_active:
                    self.stats['dissolve_transitions_completed'] += 1
                    logger.info("Pattern dissolve transition completed")
                
                return result
            else:
                return self._get_current_led_array()
                
        except Exception as e:
            logger.error(f"Error getting rendered LED array: {e}")
            return [[0, 0, 0] for _ in range(225)]
    
    def get_led_output_with_timing(self, current_time: float) -> List[List[int]]:
        """Get LED output with time-based brightness and dissolve crossfade"""
        try:
            with self._lock:
                if not self.current_scene:
                    return [[0, 0, 0] for _ in range(EngineSettings.ANIMATION.led_count)]
                
                if self.dissolve_transition.is_active:
                    return self.dissolve_transition.update_dissolve(current_time)
                
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
    
    # ==================== Parameter-Only Change Methods ====================
    
    def change_scene_parameters_only(self, scene_id: int) -> bool:
        """
        Change scene parameters without triggering animation or dissolve
        Used by /change_scene OSC command
        """
        try:
            with self._lock:
                if scene_id not in self.scenes:
                    logger.warning(f"Scene {scene_id} not found for parameter change")
                    return False
                
                self.current_scene_id = scene_id
                self.current_scene = self.scenes[scene_id]
                
                logger.debug(f"Scene parameters set to {scene_id} (no dissolve trigger)")
                return True
                
        except Exception as e:
            logger.error(f"Error changing scene parameters: {e}")
            self.stats['errors'] += 1
            return False
    
    def change_effect_parameters_only(self, effect_id: int) -> bool:
        """
        Change effect parameters without triggering animation or dissolve
        Used by /change_effect OSC command
        """
        try:
            with self._lock:
                if not self.current_scene:
                    logger.warning("No active scene for effect parameter change")
                    return False
                
                if effect_id < 0 or effect_id >= len(self.current_scene.effects):
                    logger.warning(f"Effect {effect_id} invalid for scene {self.current_scene_id}")
                    return False
                
                self.current_scene.current_effect_id = effect_id
                return True
                
        except Exception as e:
            logger.error(f"Error changing effect parameters: {e}")
            self.stats['errors'] += 1
            return False
    
    def change_palette_parameters_only(self, palette_id: int) -> bool:
        """
        Change palette parameters without triggering animation or dissolve
        Used by /change_palette OSC command
        """
        try:
            with self._lock:
                if not self.current_scene:
                    logger.warning("No active scene for palette parameter change")
                    return False
                
                if palette_id >= len(self.current_scene.palettes):
                    logger.warning(f"Palette {palette_id} not found in scene {self.current_scene_id}")
                    return False
                
                self.current_scene.current_palette_id = palette_id
                
                logger.debug(f"Palette parameters set to {palette_id} (no dissolve trigger)")
                return True
                
        except Exception as e:
            logger.error(f"Error changing palette parameters: {e}")
            self.stats['errors'] += 1
            return False
    
    # ==================== Pattern Change Methods ====================
    
    def apply_pattern_change(self, pattern_state) -> bool:
        """
        Apply pattern change to scene manager state
        Used by /change_pattern OSC command
        
        Args:
            pattern_state: PatternState with scene_id, effect_id, palette_id
            
        Returns:
            bool: True if pattern was applied successfully
        """
        try:
            with self._lock:
                if pattern_state.scene_id not in self.scenes:
                    logger.error(f"Scene {pattern_state.scene_id} not found")
                    return False
                
                target_scene = self.scenes[pattern_state.scene_id]
                
                if pattern_state.effect_id >= len(target_scene.effects):
                    logger.error(f"Effect {pattern_state.effect_id} not found in scene {pattern_state.scene_id}")
                    return False
                
                if pattern_state.palette_id >= len(target_scene.palettes):
                    logger.error(f"Palette {pattern_state.palette_id} not found in scene {pattern_state.scene_id}")
                    return False
                
                self.current_scene_id = pattern_state.scene_id
                self.current_scene = target_scene
                self.current_scene.current_effect_id = pattern_state.effect_id
                self.current_scene.current_palette_id = pattern_state.palette_id
                
                self.stats['pattern_changes'] += 1
                logger.debug(f"Pattern applied: {pattern_state.scene_id}/{pattern_state.effect_id}/{pattern_state.palette_id}")
                
                return True
                
        except Exception as e:
            logger.error(f"Error applying pattern change: {e}")
            self.stats['errors'] += 1
            return False
    
    def start_fade_in_dissolve(self, pattern_state) -> bool:
        """
        Start fade-in dissolve for first-time pattern activation
        Creates dissolve from black to new pattern
        
        Args:
            pattern_state: Target pattern state
            
        Returns:
            bool: True if dissolve was started, False if no dissolve pattern set
        """
        try:
            if self.dissolve_patterns.current_pattern_id is None:
                logger.debug("No dissolve pattern set - direct pattern activation")
                return False
            
            pattern_data = self.dissolve_patterns.get_pattern(self.dissolve_patterns.current_pattern_id)
            if not pattern_data:
                logger.debug("Dissolve pattern not found - direct pattern activation")
                return False
            
            black_pattern = PatternState(
                scene_id=pattern_state.scene_id,
                effect_id=pattern_state.effect_id,
                palette_id=pattern_state.palette_id
            )
            
            led_count = self.current_scene.led_count if self.current_scene else 225
            
            self.dissolve_transition.start_dissolve(
                black_pattern,  
                pattern_state,  
                pattern_data,
                led_count
            )
            
            self.stats['fade_in_transitions'] += 1
            logger.info(f"Fade-in dissolve started for pattern {pattern_state.scene_id}/{pattern_state.effect_id}/{pattern_state.palette_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error starting fade-in dissolve: {e}")
            return False
    
    def start_crossfade_dissolve(self, old_pattern, new_pattern) -> bool:
        """
        Start crossfade dissolve between two patterns
        Both patterns continue animating during transition
        
        Args:
            old_pattern: Current pattern state
            new_pattern: Target pattern state
            
        Returns:
            bool: True if dissolve was started, False if no dissolve pattern set
        """
        try:
            if self.dissolve_patterns.current_pattern_id is None:
                logger.debug("No dissolve pattern set - direct pattern change")
                return False
            
            pattern_data = self.dissolve_patterns.get_pattern(self.dissolve_patterns.current_pattern_id)
            if not pattern_data:
                logger.debug("Dissolve pattern not found - direct pattern change")
                return False
            
            led_count = self.current_scene.led_count if self.current_scene else 225
            
            self.dissolve_transition.start_dissolve(
                old_pattern,
                new_pattern,
                pattern_data,
                led_count
            )
            
            self.stats['crossfade_transitions'] += 1
            logger.info(f"Crossfade dissolve started: {old_pattern.scene_id}/{old_pattern.effect_id}/{old_pattern.palette_id} -> {new_pattern.scene_id}/{new_pattern.effect_id}/{new_pattern.palette_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error starting crossfade dissolve: {e}")
            return False
    
    # ==================== Legacy Scene Operations ====================
    
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
                return True
                
        except Exception as e:
            logger.error(f"Error updating palette color: {e}")
            self.stats['errors'] += 1
            return False
    
    # ==================== Helper Methods ====================
    
    def _create_current_pattern_state(self):
        """Create pattern state for current scene configuration"""
        if not self.current_scene:
            return None
        
        return PatternState(
            scene_id=self.current_scene_id,
            effect_id=self.current_scene.current_effect_id,
            palette_id=self.current_scene.current_palette_id
        )
    
    def _start_legacy_dissolve_if_enabled(self, old_pattern, new_pattern):
        """Start legacy dissolve if pattern is set (for backward compatibility)"""
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
    
    def get_scene_info_for_scene(self, scene_id: int) -> Dict[str, Any]:
        """
        Get scene information for a specific scene (not necessarily current)
        Used for validation in /change_pattern
        """
        with self._lock:
            if scene_id not in self.scenes:
                return {
                    "error": f"Scene {scene_id} not found",
                    "available_scenes": list(self.scenes.keys())
                }
            
            scene = self.scenes[scene_id]
            
            available_effects = []
            if hasattr(scene, 'effects'):
                available_effects = list(range(len(scene.effects)))
            
            return {
                "scene_id": scene_id,
                "led_count": scene.led_count,
                "fps": scene.fps,
                "available_effects": available_effects,
                "available_palettes": list(range(len(scene.palettes))),
                "effects_count": len(scene.effects),
                "palettes_count": len(scene.palettes)
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
                logger.info("Dissolve transition force stopped")
    
    def shutdown(self):
        """Shutdown the scene manager"""
        with self._lock:
            self.dissolve_transition.is_active = False
            
            self._change_callbacks.clear()
            
            logger.info("SceneManager shutdown complete")