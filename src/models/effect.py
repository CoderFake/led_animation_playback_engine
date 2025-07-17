"""
Effect model -  tructure with zero-origin IDs
"""

from typing import Dict, List, Any
from dataclasses import dataclass, field
import time
from src.utils.color_utils import ColorUtils
from .segment import Segment


@dataclass
class Effect:
    """
    Simplified Effect model containing only segments.
    Uses zero-origin ID system. led_count and fps moved to Scene level.
    """
    
    effect_id: int
    segments: Dict[str, Segment] = field(default_factory=dict)
    
    def add_segment(self, segment: Segment):
        """
        Add a segment to the effect
        """
        self.segments[str(segment.segment_id)] = segment
        
    def update_animation(self, delta_time: float):
        """
        Update the animation for all segments
        """
        for segment in self.segments.values():
            segment.update_position(delta_time)
    
    def render_to_led_array(self, palette: List[List[int]], current_time: float, 
                           led_array: List[List[int]]) -> None:
        """
        Render all segments to LED array with timing and fractional positioning
        """
        ColorUtils.reset_frame_contributions()
    
        for led in led_array:
            led[0] = led[1] = led[2] = 0
        
        for segment in self.segments.values():
            segment.render_to_led_array(palette, current_time, led_array)
        
        ColorUtils.finalize_frame_blending(led_array)
    
    def get_led_output(self, palette: List[List[int]]) -> List[List[int]]:
        """
        Calculate the final LED output for this effect (legacy method)
        This method is kept for backward compatibility but should use render_to_led_array
        """
        max_led_index = 0
        for segment in self.segments.values():
            segment_end = int(segment.current_position) + segment.get_total_led_count()
            max_led_index = max(max_led_index, segment_end)
        
        led_count = max(225, max_led_index) 
        led_colors = [[0, 0, 0] for _ in range(led_count)]
        current_time = time.time()
        
        self.render_to_led_array(palette, current_time, led_colors)
        
        return led_colors
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the effect to a dictionary
        """
        return {
            "effect_id": self.effect_id, 
            "segments": {k: v.to_dict() for k, v in self.segments.items()}
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Effect':
        """
        Create an effect from a dictionary
        """
        try:
            effect_id = data.get("effect_id", data.get("effect_ID", 0))
            
            effect = cls(effect_id=effect_id)
            
            segments_data = data.get("segments", {})
            for seg_id, seg_data in segments_data.items():
                segment = Segment.from_dict(seg_data)
                effect.segments[seg_id] = segment
                
            return effect
            
        except Exception as e:
            import sys
            print(f"Error creating effect from dict: {e}", file=sys.stderr, flush=True)
            return cls(effect_id=0)
    
    def get_active_segments_count(self) -> int:
        """
        Count the number of active segments (with movement or visible LEDs)
        """
        return sum(1 for segment in self.segments.values() if segment.is_active())
    
    def set_speed_multiplier(self, multiplier: float):
        """
        Set the speed multiplier for all segments
        Supports expanded range 0-1023%
        """
        multiplier = max(0.0, min(10.23, multiplier))  
        
        for segment in self.segments.values():
            if segment.move_speed > 0:
                segment.move_speed = abs(segment.move_speed) * multiplier
            elif segment.move_speed < 0:
                segment.move_speed = -abs(segment.move_speed) * multiplier
    
    def reset_all_positions(self):
        """
        Reset all segments to their initial positions
        """
        for segment in self.segments.values():
            segment.reset_position()
    
    def get_total_led_count(self) -> int:
        """
        Get total LED count used by all segments
        """
        total = 0
        for segment in self.segments.values():
            segment_end = int(segment.current_position) + segment.get_total_led_count()
            total = max(total, segment_end)
        return total
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get effect statistics
        """
        return {
            "effect_id": self.effect_id,
            "segments_count": len(self.segments),
            "active_segments": self.get_active_segments_count(),
            "total_led_usage": self.get_total_led_count()
        }