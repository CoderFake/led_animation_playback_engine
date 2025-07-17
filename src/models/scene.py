"""
Scene model - Zero-origin IDs with led_count and fpse
"""

from typing import List, Any, Dict, Optional
from dataclasses import dataclass, field
import time

from .effect import Effect


@dataclass 
class Scene:
    """
    Scene model with zero-origin IDs and palettes as arrays.
    Contains led_count and fps at scene level instead of effect level.
    """
    
    scene_id: int
    led_count: int = 225
    fps: int = 60
    current_effect_id: int = 0
    current_palette_id: int = 0
    palettes: List[List[List[int]]] = field(default_factory=list)
    effects: List[Effect] = field(default_factory=list)
    
    def __post_init__(self):
        """
        Initialize default palettes and effects if empty
        """
        if not self.palettes:
            self.palettes = [
                [[255, 255, 255], [255, 0, 0], [0, 255, 0], [0, 0, 255], [255, 255, 0], [255, 0, 255]]
            ]
        
        if not self.effects:
            self.effects = [Effect(effect_id=0)]
    
    def add_effect(self, effect: Effect):
        """
        Add an effect to the scene (ensure array is large enough)
        """
        while len(self.effects) <= effect.effect_id:
            self.effects.append(Effect(effect_id=len(self.effects)))
        
        self.effects[effect.effect_id] = effect
        
    def get_current_effect(self) -> Optional[Effect]:
        if 0 <= self.current_effect_id < len(self.effects):
            return self.effects[self.current_effect_id]
        return None
    
    def get_current_palette(self) -> List[List[int]]:
        """
        Get the currently active palette using zero-origin indexing
        """
        if 0 <= self.current_palette_id < len(self.palettes):
            return self.palettes[self.current_palette_id]
        
        return [[255, 255, 255], [255, 0, 0], [0, 255, 0], [0, 0, 255], [255, 255, 0], [255, 0, 255]]
    
    def switch_effect(self, effect_id: int, palette_id: int = None):
        """
        Switch the effect and optionally the palette using zero-origin IDs
        """
        if 0 <= effect_id < len(self.effects):
            self.current_effect_id = effect_id
            
        if palette_id is not None and 0 <= palette_id < len(self.palettes):
            self.current_palette_id = palette_id
    
    def get_total_led_count(self) -> int:
        """
        Calculate total LED count from segments
        """
        try:
            max_led_index = 0
            
            for effect in self.effects:
                for segment in effect.segments.values():
                    segment_end = int(segment.current_position) + segment.get_total_led_count()
                    max_led_index = max(max_led_index, segment_end)
            
            return max(self.led_count, max_led_index)
            
        except Exception:
            return self.led_count
    
    def get_led_output(self) -> List[List[int]]:
        """
        Get the final LED output for the current scene (legacy method)
        """
        current_effect = self.get_current_effect()
        if current_effect:
            palette = self.get_current_palette()
            total_leds = self.get_total_led_count()
            led_array = [[0, 0, 0] for _ in range(total_leds)]
            current_effect.render_to_led_array(palette, time.time(), led_array)
            return led_array
        return [[0, 0, 0] for _ in range(self.led_count)]
    
    def get_led_output_with_timing(self, current_time: float) -> List[List[int]]:
        """
        Get LED output with time-based brightness and fractional positioning
        """
        current_effect = self.get_current_effect()
        if not current_effect:
            return [[0, 0, 0] for _ in range(self.led_count)]
        
        total_leds = self.get_total_led_count()
        led_array = [[0, 0, 0] for _ in range(total_leds)]
        palette = self.get_current_palette()
        
        current_effect.render_to_led_array(palette, current_time, led_array)
        
        return led_array
    
    def add_palette(self, palette: List[List[int]], palette_id: int = None):
        """
        Add a palette at specific index (zero-origin)
        """
        if palette_id is None:
            palette_id = len(self.palettes)
        
        while len(self.palettes) <= palette_id:
            self.palettes.append([[255, 255, 255]] * 6)
        
        self.palettes[palette_id] = palette
    
    def update_palette_color(self, palette_id: int, color_id: int, rgb: List[int]) -> bool:
        """
        Update specific color in palette using zero-origin indexing
        """
        if not (0 <= palette_id < len(self.palettes)):
            return False
        
        if not (0 <= color_id < len(self.palettes[palette_id])):
            return False
        
        self.palettes[palette_id][color_id] = rgb[:3]
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the scene to a dictionary for serialization
        """
        return {
            "scene_id": self.scene_id,
            "led_count": self.led_count,
            "fps": self.fps,
            "current_effect_id": self.current_effect_id,
            "current_palette_id": self.current_palette_id,
            "palettes": self.palettes,
            "effects": [effect.to_dict() for effect in self.effects]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Scene':
        """
        Create a scene from a dictionary with format conversion
        """
        try:
            scene_id = data.get("scene_id", data.get("scene_ID", 0))
            led_count = data.get("led_count", 225)
            fps = data.get("fps", 60)
            current_effect_id = data.get("current_effect_id", data.get("current_effect_ID", 0))
            
            current_palette = data.get("current_palette_id", data.get("current_palette", "A"))
            if isinstance(current_palette, str):
                current_palette_id = ord(current_palette.upper()) - ord('A') if current_palette else 0
            else:
                current_palette_id = current_palette
            
            scene = cls(
                scene_id=scene_id,
                led_count=led_count,
                fps=fps,
                current_effect_id=current_effect_id,
                current_palette_id=current_palette_id
            )
            
            palettes_data = data.get("palettes", {})
            if isinstance(palettes_data, dict):
                max_id = 0
                for key in palettes_data.keys():
                    if isinstance(key, str):
                        palette_id = ord(key.upper()) - ord('A')
                    else:
                        palette_id = int(key)
                    max_id = max(max_id, palette_id)
                
                scene.palettes = [[[255, 255, 255]] * 6 for _ in range(max_id + 1)]
                
                for key, palette in palettes_data.items():
                    if isinstance(key, str):
                        palette_id = ord(key.upper()) - ord('A')
                    else:
                        palette_id = int(key)
                    
                    if 0 <= palette_id < len(scene.palettes):
                        scene.palettes[palette_id] = palette
            else:
                scene.palettes = palettes_data or [[[255, 255, 255]] * 6]
            
            effects_data = data.get("effects", {})
            if isinstance(effects_data, dict):
                max_id = 0
                for key in effects_data.keys():
                    effect_id = int(key)
                    max_id = max(max_id, effect_id)
                
                scene.effects = [Effect(effect_id=i) for i in range(max_id + 1)]
                
                for key, effect_data in effects_data.items():
                    effect_id = int(key)
                    if 0 <= effect_id < len(scene.effects):
                        effect = Effect.from_dict(effect_data)
                        scene.effects[effect_id] = effect
            else:
                if isinstance(effects_data, list):
                    scene.effects = []
                    for effect_data in effects_data:
                        effect = Effect.from_dict(effect_data)
                        scene.add_effect(effect)
                else:
                    scene.effects = [Effect(effect_id=0)]
            
            return scene
            
        except Exception as e:
            import sys
            print(f"Error creating scene from dict: {e}", file=sys.stderr, flush=True)
            return cls(scene_id=0)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get scene statistics
        """
        current_effect = self.get_current_effect()
        total_segments = len(current_effect.segments) if current_effect else 0
        
        return {
            "scene_id": self.scene_id,
            "led_count": self.led_count,
            "fps": self.fps,
            "effects_count": len(self.effects),
            "palettes_count": len(self.palettes),
            "segments_count": total_segments,
            "current_effect_id": self.current_effect_id,
            "current_palette_id": self.current_palette_id,
            "total_led_count": self.get_total_led_count()
        }
    
    def validate(self) -> bool:
        """
        Validate scene data integrity
        """
        try:
            if not isinstance(self.scene_id, int) or self.scene_id < 0:
                return False
            
            if not isinstance(self.led_count, int) or self.led_count <= 0:
                return False
            
            if not isinstance(self.fps, int) or self.fps <= 0:
                return False
            
            if not (0 <= self.current_effect_id < len(self.effects)):
                return False
            
            if not (0 <= self.current_palette_id < len(self.palettes)):
                return False
            
            for palette in self.palettes:
                if not isinstance(palette, list) or len(palette) != 6:
                    return False
                for color in palette:
                    if not isinstance(color, list) or len(color) != 3:
                        return False
                    if not all(isinstance(c, int) and 0 <= c <= 255 for c in color):
                        return False
            
            for effect in self.effects:
                if not effect.validate() if hasattr(effect, 'validate') else True:
                    return False
            
            return True
            
        except Exception:
            return False