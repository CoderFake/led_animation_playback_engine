"""
Effect model - Defines the Effect data structure.
"""

from typing import Dict, List, Any
from dataclasses import dataclass, field

from .segment import Segment


@dataclass
class Effect:
    """
    Effect model containing multiple segments.
    """
    
    effect_id: int
    led_count: int = 225
    fps: int = 60
    time: float = 0.0
    current_palette: str = "A"
    segments: Dict[str, Segment] = field(default_factory=dict)
    
    def add_segment(self, segment: Segment):
        """
        Add a segment to the effect.
        """
        self.segments[str(segment.segment_id)] = segment
        
    def update_animation(self, delta_time: float):
        """
        Update the animation for all segments.
        """
        self.time += delta_time
        for segment in self.segments.values():
            segment.update_position(delta_time)
            
    def get_led_output(self, palette: List[List[int]]) -> List[List[int]]:
        """
        Calculate the final LED output for this effect.
        """
        led_colors = [[0, 0, 0] for _ in range(self.led_count)]
        
        for segment in self.segments.values():
            segment_colors = segment.get_led_colors(palette)
            start_pos = int(segment.current_position)
            
            for i, color in enumerate(segment_colors):
                led_index = start_pos + i
                if 0 <= led_index < self.led_count:
                    for j in range(3):
                        led_colors[led_index][j] = max(led_colors[led_index][j], color[j])
                        
        return led_colors
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the effect to a dictionary.
        """
        return {
            "effect_ID": self.effect_id,
            "led_count": self.led_count,
            "fps": self.fps,
            "time": self.time,
            "current_palette": self.current_palette,
            "segments": {k: v.to_dict() for k, v in self.segments.items()}
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Effect':
        """
        Create an effect from a dictionary.
        """
        effect = cls(
            effect_id=data["effect_ID"],
            led_count=data["led_count"],
            fps=data["fps"],
            time=data["time"],
            current_palette=data["current_palette"]
        )
        
        for seg_id, seg_data in data["segments"].items():
            segment = Segment.from_dict(seg_data)
            effect.segments[seg_id] = segment
            
        return effect
    
    def get_active_segments_count(self) -> int:
        """
        Count the number of active segments (with movement).
        """
        return sum(1 for segment in self.segments.values() if segment.move_speed != 0)
    
    def set_speed_multiplier(self, multiplier: float):
        """
        Set the speed multiplier for all segments.
        """
        for segment in self.segments.values():
            if segment.move_speed > 0:
                segment.move_speed = abs(segment.move_speed) * multiplier
            elif segment.move_speed < 0:
                segment.move_speed = -abs(segment.move_speed) * multiplier