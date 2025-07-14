"""
Segment model - Complete rewrite following exact spec
Zero-origin IDs with time-based dimmer and fractional positioning
"""

from typing import List, Any, Dict
from dataclasses import dataclass, field
import time
import math


@dataclass
class Segment:
    """
    LED Segment model with time-based brightness and fractional positioning.
    Uses zero-origin ID system and supports speed range 0-1023%.
    """
    
    segment_id: int
    color: List[int] = field(default_factory=lambda: [0])
    transparency: List[float] = field(default_factory=lambda: [1.0])
    length: List[int] = field(default_factory=lambda: [10])
    move_speed: float = 0.0
    move_range: List[int] = field(default_factory=lambda: [0, 224])
    initial_position: int = 0
    current_position: float = 0.0
    is_edge_reflect: bool = True
    dimmer_time: List[List[int]] = field(default_factory=lambda: [[1000, 0, 100]])
    segment_start_time: float = 0.0
    
    def __post_init__(self):
        """Initialize segment timing and validate data"""
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
        
        self.segment_start_time = time.time()
        
        if not self.dimmer_time or not isinstance(self.dimmer_time[0], list):
            self.dimmer_time = [[1000, 0, 100]]
    
    def reset_animation_timing(self):
        """Reset timing when segment direction changes or position resets"""
        self.segment_start_time = time.time()
    
    def get_brightness_at_time(self, current_time: float) -> float:
        """Get brightness based on elapsed time since segment start"""
        try:
            if not self.dimmer_time:
                return 1.0
            
            elapsed_ms = (current_time - self.segment_start_time) * 1000
            
            total_cycle_ms = sum(transition[0] for transition in self.dimmer_time)
            if total_cycle_ms <= 0:
                return 1.0
            
            elapsed_ms = elapsed_ms % total_cycle_ms
            
            current_time_ms = 0
            for duration_ms, start_brightness, end_brightness in self.dimmer_time:
                if elapsed_ms <= current_time_ms + duration_ms:
                    if duration_ms > 0:
                        progress = (elapsed_ms - current_time_ms) / duration_ms
                    else:
                        progress = 0.0
                    
                    brightness = start_brightness + (end_brightness - start_brightness) * progress
                    result = max(0.0, min(1.0, brightness / 100.0))
                    
                    return result
                current_time_ms += duration_ms
            
            if self.dimmer_time:
                last_brightness = self.dimmer_time[-1][2] 
                return max(0.0, min(1.0, last_brightness / 100.0))
            
            return 1.0
            
        except Exception:
            return 1.0 
    
    def update_position(self, delta_time: float):
        """Update position with expanded speed range 0-1023% and handle boundary conditions"""
        if abs(self.move_speed) < 0.001:
            return
            
        self.current_position += self.move_speed * delta_time
        
        if self.is_edge_reflect and len(self.move_range) >= 2:
            min_pos, max_pos = self.move_range[0], self.move_range[1]
            
            if self.current_position <= min_pos:
                self.current_position = min_pos
                self.move_speed = abs(self.move_speed)
                self.reset_animation_timing() 
            elif self.current_position >= max_pos:
                self.current_position = max_pos
                self.move_speed = -abs(self.move_speed)
                self.reset_animation_timing() 
        elif not self.is_edge_reflect and len(self.move_range) >= 2:
            min_pos, max_pos = self.move_range[0], self.move_range[1]
            range_size = max_pos - min_pos
            if range_size > 0:
                relative_pos = (self.current_position - min_pos) % range_size
                self.current_position = min_pos + relative_pos
    
    def get_led_colors_with_timing(self, palette: List[List[int]], current_time: float) -> List[List[int]]:
        """Get LED colors with time-based brightness and palette as array (zero-origin)"""
        if not self.color or not palette:
            return []
        
        brightness_factor = self.get_brightness_at_time(current_time)
        
        colors = []
        
        try:
            for part_index in range(len(self.length)):
                part_length = max(0, self.length[part_index])
                
                if part_length == 0:
                    continue
                
                color_index = self.color[part_index] if part_index < len(self.color) else 0
                alpha = self.transparency[part_index] if part_index < len(self.transparency) else 1.0
                
                for led_in_part in range(part_length):
                    if 0 <= color_index < len(palette):
                        base_color = palette[color_index][:3] if len(palette[color_index]) >= 3 else [0, 0, 0]
                    else:
                        base_color = [0, 0, 0]
                    
                    final_color = [
                        max(0, min(255, int(c * alpha * brightness_factor)))
                        for c in base_color
                    ]
                    colors.append(final_color)
                
            if len(self.color) > len(self.length):
                for extra_index in range(len(self.length), len(self.color)):
                    color_index = self.color[extra_index]
                    if 0 <= color_index < len(palette):
                        base_color = palette[color_index][:3] if len(palette[color_index]) >= 3 else [0, 0, 0]
                    else:
                        base_color = [0, 0, 0]
                    
                    alpha = self.transparency[extra_index] if extra_index < len(self.transparency) else 1.0
                    final_color = [
                        max(0, min(255, int(c * alpha * brightness_factor)))
                        for c in base_color
                    ]
                    colors.append(final_color)
            
        
            return colors
            
        except Exception as e:
            return []
    
    def render_to_led_array(self, palette: List[List[int]], current_time: float, 
                           led_array: List[List[int]]) -> None:
        """Render segment to LED array with fractional positioning and fade effects"""
        segment_colors = self.get_led_colors_with_timing(palette, current_time)
        
        if not segment_colors:
            return
        
        try:
            base_position = int(self.current_position)
            fractional_part = self.current_position - base_position
            
            for i, color in enumerate(segment_colors):
                led_index = base_position + i
                
                if 0 <= led_index < len(led_array):
                    if len(segment_colors) > 1:
                        if i == 0:
                            fade_factor = fractional_part
                            faded_color = [int(c * fade_factor) for c in color]
                        elif i == len(segment_colors) - 1:
                            fade_factor = 1.0 - fractional_part
                            faded_color = [int(c * fade_factor) for c in color]
                        else:
                            faded_color = color
                    else:
                        faded_color = color
                    
                    for j in range(3):
                        led_array[led_index][j] = min(255, led_array[led_index][j] + faded_color[j])
                        
        except Exception as e:
            pass
    
    def get_total_led_count(self) -> int:
        """Get total number of LEDs this segment will generate"""
        try:
            total = sum(max(0, length) for length in self.length)
            
            if len(self.color) > len(self.length):
                total += len(self.color) - len(self.length)
            
            return max(0, total)
        except Exception:
            return 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the segment to a dictionary for JSON serialization"""
        return {
            "segment_id": self.segment_id, 
            "color": self.color,
            "transparency": self.transparency,
            "length": self.length,
            "move_speed": self.move_speed,
            "move_range": self.move_range,
            "initial_position": self.initial_position,
            "current_position": self.current_position,
            "is_edge_reflect": self.is_edge_reflect,
            "dimmer_time": self.dimmer_time  
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Segment':
        """Create a segment from a dictionary with format conversion"""
        try:
            dimmer_time = data.get("dimmer_time", [[1000, 0, 100]])
            if dimmer_time and isinstance(dimmer_time[0], (int, float)):
                dimmer_time = cls.convert_legacy_dimmer_time(dimmer_time)
            
            segment = cls(
                segment_id=data.get("segment_id", data.get("segment_ID", 0)),  
                color=data.get("color", [0]),
                transparency=data.get("transparency", [1.0]),
                length=data.get("length", [1]),
                move_speed=data.get("move_speed", 0.0),
                move_range=data.get("move_range", [0, 224]),
                initial_position=data.get("initial_position", 0),
                current_position=data.get("current_position", 0.0),
                is_edge_reflect=data.get("is_edge_reflect", True),
                dimmer_time=dimmer_time
            )
            
            if segment.current_position == 0.0:
                segment.current_position = float(segment.initial_position)
            
            return segment
            
        except Exception as e:
            import sys
            print(f"Error creating segment from dict: {e}", file=sys.stderr, flush=True)
            return cls(segment_id=0)
    
    @staticmethod
    def convert_legacy_dimmer_time(old_format: List[int]) -> List[List[int]]:
        """Convert 1D position-based dimmer_time to 2D time-based format"""
        if not old_format or len(old_format) < 2:
            return [[1000, 0, 100]] 
        
        new_format = []
        default_duration = 1000  
        
        for i in range(len(old_format) - 1):
            start_brightness = old_format[i]
            end_brightness = old_format[i + 1]
            new_format.append([default_duration, start_brightness, end_brightness])
        
        return new_format
    
    def reset_position(self):
        """Reset the position to the initial position and restart timing"""
        self.current_position = float(self.initial_position)
        self.reset_animation_timing()
    
    def is_active(self) -> bool:
        """Check if the segment is active (has visible LEDs)"""
        try:
            return (any(c >= 0 for c in self.color) and 
                    sum(max(0, length) for length in self.length) > 0 and
                    any(t > 0 for t in self.transparency))
        except Exception:
            return False
    
    def validate(self) -> bool:
        """Validate segment data integrity"""
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
            
            if self.dimmer_time:
                for transition in self.dimmer_time:
                    if not isinstance(transition, list) or len(transition) != 3:
                        return False
                    if not all(isinstance(x, (int, float)) for x in transition):
                        return False
            
            return True
            
        except Exception:
            return False