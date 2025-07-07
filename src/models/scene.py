"""
Scene model - Defines the Scene data structure.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

from .effect import Effect


@dataclass 
class Scene:
    """
    Scene model containing effects and palettes.
    """
    
    scene_id: int
    current_effect_id: int = 1
    current_palette: str = "A"
    palettes: Dict[str, List[List[int]]] = field(default_factory=dict)
    effects: Dict[str, Effect] = field(default_factory=dict)
    fade_params: List[int] = field(default_factory=lambda: [100, 200, 100])
    
    def add_effect(self, effect: Effect):
        """
        Add an effect to the scene.
        """
        self.effects[str(effect.effect_id)] = effect
        
    def get_current_effect(self) -> Optional[Effect]:
        """
        Get the currently active effect.
        """
        return self.effects.get(str(self.current_effect_id))
    
    def get_current_palette(self) -> List[List[int]]:
        """
        Get the currently active palette.
        """
        return self.palettes.get(self.current_palette, [[255, 255, 255]] * 6)
    
    def switch_effect(self, effect_id: int, palette: str = None):
        """
        Switch the effect and optionally the palette.
        """
        if str(effect_id) in self.effects:
            self.current_effect_id = effect_id
            
        if palette and palette in self.palettes:
            self.current_palette = palette
            
    def get_led_output(self) -> List[List[int]]:
        """
        Get the final LED output for the current scene.
        """
        current_effect = self.get_current_effect()
        if current_effect:
            palette = self.get_current_palette()
            return current_effect.get_led_output(palette)
        return [[0, 0, 0] for _ in range(225)]
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the scene to a dictionary for serialization.
        """
        return {
            "scene_ID": self.scene_id,
            "current_effect_ID": self.current_effect_id,
            "current_palette": self.current_palette,
            "palettes": self.palettes,
            "effects": {k: v.to_dict() for k, v in self.effects.items()}
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Scene':
        """
        Create a scene from a dictionary.
        """
        scene = cls(
            scene_id=data["scene_ID"],
            current_effect_id=data["current_effect_ID"],
            current_palette=data["current_palette"],
            palettes=data["palettes"]
        )
        
        for eff_id, eff_data in data["effects"].items():
            effect = Effect.from_dict(eff_data)
            scene.effects[eff_id] = effect
            
        return scene
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get scene statistics.
        """
        current_effect = self.get_current_effect()
        total_segments = len(current_effect.segments) if current_effect else 0
        
        return {
            "scene_id": self.scene_id,
            "effects_count": len(self.effects),
            "palettes_count": len(self.palettes),
            "segments_count": total_segments,
            "current_effect_id": self.current_effect_id,
            "current_palette": self.current_palette
        }