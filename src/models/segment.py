"""
Segment model - Accurate LED calculation for large arrays and variable lengths
"""

from typing import List, Any, Dict
from dataclasses import dataclass, field
import math


@dataclass
class Segment:
    """
    LED Segment model representing a moving light segment.
    """
    
    segment_id: int
    color: List[int] = field(default_factory=lambda: [0, 0, 0, 0])
    transparency: List[float] = field(default_factory=lambda: [1.0, 1.0, 1.0, 1.0])
    length: List[int] = field(default_factory=lambda: [10, 10, 10])
    move_speed: float = 0.0
    move_range: List[int] = field(default_factory=lambda: [0, 224])
    initial_position: int = 0
    current_position: float = 0.0
    is_edge_reflect: bool = True
    dimmer_time: List[int] = field(default_factory=lambda: [0, 100, 200, 100, 0])
    dimmer_time_ratio: float = 1.0
    gradient: bool = False
    fade: bool = False
    gradient_colors: List[int] = field(default_factory=lambda: [0, -1, -1])
    
    def __post_init__(self):
        """
        Validate and initialize segment data
        """
        if self.current_position == 0.0:
            self.current_position = float(self.initial_position)
        
        if not self.color:
            self.color = [0]
        
        if not self.transparency:
            self.transparency = [1.0] * len(self.color)
        
        if not self.length:
            self.length = [1] * len(self.color)
        
        while len(self.transparency) < len(self.color):
            self.transparency.append(1.0)
        
        while len(self.length) < len(self.color):
            self.length.append(1)
    
    def update_position(self, delta_time: float):
        """
        Update the position of the segment - OPTIMIZED for performance
        """
        if abs(self.move_speed) < 0.001:
            return
            
        self.current_position += self.move_speed * delta_time
        
        if self.is_edge_reflect and len(self.move_range) >= 2:
            min_pos, max_pos = self.move_range[0], self.move_range[1]
            
            if self.current_position <= min_pos:
                self.current_position = min_pos
                self.move_speed = abs(self.move_speed)
            elif self.current_position >= max_pos:
                self.current_position = max_pos
                self.move_speed = -abs(self.move_speed)
        elif not self.is_edge_reflect and len(self.move_range) >= 2:
            min_pos, max_pos = self.move_range[0], self.move_range[1]
            range_size = max_pos - min_pos
            if range_size > 0:
                relative_pos = (self.current_position - min_pos) % range_size
                self.current_position = min_pos + relative_pos
                
    def get_led_colors(self, palette: List[List[int]]) -> List[List[int]]:
        """
        Calculate LED colors for this segment
        """
        if not self.color or not palette:
            return []
        
        colors = []
        current_led_index = 0
        
        try:
            total_length = sum(max(0, length) for length in self.length)
            
            if total_length == 0:
                for i in range(len(self.color)):
                    if len(self.color) > len(self.length):
                        colors.append(self._get_single_led_color(i, palette, 0))
                return colors
            
            for part_index in range(len(self.length)):
                part_length = max(0, self.length[part_index])
                
                if part_length == 0:
                    continue
                
                color_index = self.color[part_index] if part_index < len(self.color) else 0
                transparency = self.transparency[part_index] if part_index < len(self.transparency) else 1.0
                
                for led_in_part in range(part_length):
                    led_color = self._calculate_led_color(
                        color_index, transparency, current_led_index, 
                        total_length, palette, part_index, led_in_part, part_length
                    )
                    colors.append(led_color)
                    current_led_index += 1
            
            if len(self.color) > len(self.length):
                for extra_index in range(len(self.length), len(self.color)):
                    led_color = self._get_single_led_color(extra_index, palette, current_led_index)
                    colors.append(led_color)
                    current_led_index += 1
            
            return colors
            
        except Exception as e:
            import sys
            print(f"Error in get_led_colors: {e}", file=sys.stderr, flush=True)
            return [[0, 0, 0] for _ in range(max(1, sum(max(0, l) for l in self.length)))]
    
    def _calculate_led_color(self, color_index: int, transparency: float, 
                           current_led_index: int, total_length: int, palette: List[List[int]],
                           part_index: int, led_in_part: int, part_length: int) -> List[int]:
        """
        Calculate color for a single LED with all effects applied
        """
        try:
            if not (0 <= color_index < len(palette)):
                return [0, 0, 0]
            
            base_color = palette[color_index][:3] if len(palette[color_index]) >= 3 else [0, 0, 0]
            
            brightness = 1.0
            if self.fade and total_length > 0:
                brightness = self._get_brightness_at_position(current_led_index, total_length)
            
            if self.gradient and part_length > 1:
                gradient_factor = led_in_part / (part_length - 1)
                brightness *= self._apply_gradient(gradient_factor, part_index)
            
            final_transparency = max(0.0, min(1.0, transparency))
            final_brightness = max(0.0, min(1.0, brightness))
            
            final_color = [
                max(0, min(255, int(c * final_transparency * final_brightness)))
                for c in base_color
            ]
            
            return final_color
            
        except Exception:
            return [0, 0, 0]
    
    def _get_single_led_color(self, color_index_in_array: int, palette: List[List[int]], led_position: int) -> List[int]:
        """
        Get color for single LED (extra colors beyond length array)
        """
        try:
            if color_index_in_array >= len(self.color):
                return [0, 0, 0]
            
            color_index = self.color[color_index_in_array]
            if not (0 <= color_index < len(palette)):
                return [0, 0, 0]
            
            base_color = palette[color_index][:3] if len(palette[color_index]) >= 3 else [0, 0, 0]
            
            transparency = 1.0
            if color_index_in_array < len(self.transparency):
                transparency = self.transparency[color_index_in_array]
            
            brightness = 1.0
            if self.fade:
                brightness = self._get_brightness_at_position(led_position, max(1, led_position + 1))
            
            final_transparency = max(0.0, min(1.0, transparency))
            final_brightness = max(0.0, min(1.0, brightness))
            
            final_color = [
                max(0, min(255, int(c * final_transparency * final_brightness)))
                for c in base_color
            ]
            
            return final_color
            
        except Exception:
            return [0, 0, 0]
    
    def _get_brightness_at_position(self, relative_pos: int, total_length: int) -> float:
        """
        Calculate brightness at relative position - OPTIMIZED
        """
        try:
            if not self.fade or not self.dimmer_time or total_length <= 0:
                return 1.0
            
            dimmer_length = len(self.dimmer_time)
            if dimmer_length <= 1:
                return self.dimmer_time[0] / 100.0 if self.dimmer_time else 1.0
            
            progress = min(1.0, max(0.0, relative_pos / total_length))
            dimmer_pos = progress * (dimmer_length - 1)
            
            index = int(dimmer_pos)
            fraction = dimmer_pos - index
            
            if index >= dimmer_length - 1:
                return max(0.0, min(1.0, self.dimmer_time[-1] / 100.0))
            
            current_value = self.dimmer_time[index]
            next_value = self.dimmer_time[index + 1]
            
            interpolated = current_value + (next_value - current_value) * fraction
            return max(0.0, min(1.0, interpolated / 100.0))
            
        except Exception:
            return 1.0
    
    def _apply_gradient(self, gradient_factor: float, part_index: int) -> float:
        """
        Apply gradient effect
        """
        try:
            if not self.gradient or not self.gradient_colors:
                return 1.0
            
            if len(self.gradient_colors) < 2:
                return 1.0
            
            start_brightness = self.gradient_colors[0] / 100.0 if self.gradient_colors[0] >= 0 else 1.0
            end_brightness = self.gradient_colors[1] / 100.0 if self.gradient_colors[1] >= 0 else 1.0
            
            brightness = start_brightness + (end_brightness - start_brightness) * gradient_factor
            return max(0.0, min(1.0, brightness))
            
        except Exception:
            return 1.0
    
    def get_total_led_count(self) -> int:
        """
        Get total number of LEDs this segment will generate
        """
        try:
            total = sum(max(0, length) for length in self.length)
            
            if len(self.color) > len(self.length):
                total += len(self.color) - len(self.length)
            
            return max(0, total)
        except Exception:
            return 0
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the segment to a dictionary for JSON serialization
        """
        return {
            "segment_ID": self.segment_id,
            "color": self.color,
            "transparency": self.transparency,
            "length": self.length,
            "move_speed": self.move_speed,
            "move_range": self.move_range,
            "initial_position": self.initial_position,
            "current_position": self.current_position,
            "is_edge_reflect": self.is_edge_reflect,
            "dimmer_time": self.dimmer_time,
            "dimmer_time_ratio": self.dimmer_time_ratio,
            "gradient": self.gradient,
            "fade": self.fade,
            "gradient_colors": self.gradient_colors
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Segment':
        """
        Create a segment from a dictionary - with validation
        """
        try:
            segment = cls(
                segment_id=data.get("segment_ID", 0),
                color=data.get("color", [0]),
                transparency=data.get("transparency", [1.0]),
                length=data.get("length", [1]),
                move_speed=data.get("move_speed", 0.0),
                move_range=data.get("move_range", [0, 224]),
                initial_position=data.get("initial_position", 0),
                current_position=data.get("current_position", 0.0),
                is_edge_reflect=data.get("is_edge_reflect", True),
                dimmer_time=data.get("dimmer_time", [0, 100, 200, 100, 0]),
                dimmer_time_ratio=data.get("dimmer_time_ratio", 1.0),
                gradient=data.get("gradient", False),
                fade=data.get("fade", False),
                gradient_colors=data.get("gradient_colors", [0, -1, -1])
            )
            
            if segment.current_position == 0.0:
                segment.current_position = float(segment.initial_position)
            
            return segment
            
        except Exception as e:
            import sys
            print(f"Error creating segment from dict: {e}", file=sys.stderr, flush=True)
            return cls(segment_id=0)
    
    def reset_position(self):
        """
        Reset the position to the initial position
        """
        self.current_position = float(self.initial_position)
    
    def is_active(self) -> bool:
        """
        Check if the segment is active (has visible LEDs)
        """
        try:
            return (any(c > 0 for c in self.color) and 
                    sum(max(0, length) for length in self.length) > 0 and
                    any(t > 0 for t in self.transparency))
        except Exception:
            return False
    
    def validate(self) -> bool:
        """
        Validate segment data integrity
        """
        try:
            if not isinstance(self.segment_id, int):
                return False
            
            if not isinstance(self.color, list) or not self.color:
                return False
            
            if not isinstance(self.length, list) or not self.length:
                return False
            
            if not isinstance(self.move_range, list) or len(self.move_range) < 2:
                return False
            
            if not all(isinstance(c, (int, float)) for c in self.color):
                return False
            
            if not all(isinstance(l, (int, float)) for l in self.length):
                return False
            
            return True
            
        except Exception:
            return False