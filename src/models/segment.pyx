# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: cdivision=True
# cython: profile=False

"""
Segment model tối ưu với Cython - tích hợp trực tiếp
Compile thành bytecode Python, không cần extension riêng biệt
"""

from typing import List, Any, Dict
from dataclasses import dataclass, field
import time
import math
import cython
from cython import Py_ssize_t
from libc.math cimport fabs
from libc.stdlib cimport malloc, free

from ..utils.validation import ValidationUtils, DataSanitizer, log_validation_error
from ..utils.logging import LoggingUtils, AnimationLogger

ctypedef struct RGBColor:
    int r
    int g
    int b

@cython.boundscheck(False)
@cython.wraparound(False)
cdef inline RGBColor apply_transparency_brightness(RGBColor base, double transparency, double brightness) nogil:
    cdef double opacity = 1.0 - transparency
    cdef RGBColor result
    
    result.r = <int>(base.r * opacity * brightness)
    result.g = <int>(base.g * opacity * brightness)
    result.b = <int>(base.b * opacity * brightness)
    
    if result.r > 255: result.r = 255
    elif result.r < 0: result.r = 0
    if result.g > 255: result.g = 255
    elif result.g < 0: result.g = 0
    if result.b > 255: result.b = 255
    elif result.b < 0: result.b = 0
    
    return result

@cython.boundscheck(False)
@cython.wraparound(False)
cdef inline void add_color_to_led(int[:, :] led_array, int index, RGBColor color) nogil:
    if index < 0 or index >= led_array.shape[0]:
        return
    
    led_array[index, 0] = led_array[index, 0] + color.r if led_array[index, 0] + color.r <= 255 else 255
    led_array[index, 1] = led_array[index, 1] + color.g if led_array[index, 1] + color.g <= 255 else 255
    led_array[index, 2] = led_array[index, 2] + color.b if led_array[index, 2] + color.b <= 255 else 255

@cython.boundscheck(False)
@cython.wraparound(False)
cdef inline RGBColor apply_fractional_fade(RGBColor color, double fractional_part, bint is_first, bint is_last) nogil:
    cdef double fade_factor = 1.0
    
    if is_first and not is_last:
        fade_factor = fractional_part if fractional_part > 0.1 else 0.1
    elif is_last and not is_first:
        fade_factor = (1.0 - fractional_part) if (1.0 - fractional_part) > 0.1 else 0.1
    
    color.r = <int>(color.r * fade_factor)
    color.g = <int>(color.g * fade_factor)
    color.b = <int>(color.b * fade_factor)
    
    return color

@dataclass
class Segment:
    """
    Segment model tối ưu với Cython - tích hợp trực tiếp
    """
    
    segment_id: int
    color: List[int] = field(default_factory=lambda: [0])
    transparency: List[float] = field(default_factory=lambda: [0.0])
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
            self.transparency = [0.0] * len(self.color)
        
        if not self.length:
            self.length = [1] * len(self.color)
        
        while len(self.transparency) < len(self.color):
            self.transparency.append(0.0)
        
        while len(self.length) < len(self.color):
            self.length.append(1)
        
        self.segment_start_time = time.time()
        
        if not self.dimmer_time or not isinstance(self.dimmer_time[0], list):
            self.dimmer_time = [[1000, 0, 100]]
        
        self._validate_dimmer_time()
    
    def _validate_dimmer_time(self):
        """Validate dimmer_time data"""
        if not self.dimmer_time:
            self.dimmer_time = [[1000, 0, 100]]
            return
        
        validated_dimmer = []
        for transition in self.dimmer_time:
            if isinstance(transition, list) and len(transition) == 3:
                duration = max(100, int(transition[0]))
                start_brightness = max(0, min(100, int(transition[1])))
                end_brightness = max(0, min(100, int(transition[2])))
                validated_dimmer.append([duration, start_brightness, end_brightness])
            else:
                validated_dimmer.append([1000, 0, 100])
        
        self.dimmer_time = validated_dimmer if validated_dimmer else [[1000, 0, 100]]
    
    def reset_animation_timing(self):
        """Reset timing when segment direction changes or position resets"""
        self.segment_start_time = time.time()
    
    @cython.boundscheck(False)
    @cython.cdivision(True)
    def get_brightness_at_time(self, double current_time) -> float:
        """Get brightness based on elapsed time - optimized"""
        cdef double elapsed_ms, total_cycle_ms, current_time_ms, progress, brightness
        cdef int duration_ms, start_brightness, end_brightness
        cdef int i
        
        if not self.dimmer_time:
            return 1.0
        
        elapsed_ms = (current_time - self.segment_start_time) * 1000.0
        
        total_cycle_ms = 0.0
        for transition in self.dimmer_time:
            total_cycle_ms += max(1, transition[0])
        
        if total_cycle_ms <= 0:
            return 1.0
        
        elapsed_ms = elapsed_ms % total_cycle_ms
        
        current_time_ms = 0.0
        for transition in self.dimmer_time:
            duration_ms = max(1, transition[0])
            start_brightness = transition[1]
            end_brightness = transition[2]
            
            if elapsed_ms <= current_time_ms + duration_ms:
                if duration_ms > 0:
                    progress = (elapsed_ms - current_time_ms) / duration_ms
                    progress = max(0.0, min(1.0, progress))
                else:
                    progress = 0.0
                
                brightness = start_brightness + (end_brightness - start_brightness) * progress
                return max(0.0, min(1.0, brightness / 100.0))
                
            current_time_ms += duration_ms
        
        if self.dimmer_time:
            return max(0.0, min(1.0, self.dimmer_time[-1][2] / 100.0))
        
        return 1.0
    
    @cython.boundscheck(False)
    def update_position(self, double delta_time):
        """Update position với tối ưu hóa"""
        cdef double old_position, min_pos, max_pos, range_size, offset
        cdef bint direction_changed = False
        
        if fabs(self.move_speed) < 0.001:
            return
        
        old_position = self.current_position
        self.current_position += self.move_speed * delta_time
        
        if self.current_position < 0:
            if len(self.move_range) >= 2:
                min_pos = self.move_range[0]
                max_pos = self.move_range[1]
                if self.is_edge_reflect:
                    self.current_position = min_pos + fabs(self.current_position)
                    if self.move_speed < 0:
                        self.move_speed = fabs(self.move_speed)
                        self.reset_animation_timing()
                else:
                    range_size = max_pos - min_pos
                    if range_size > 0:
                        self.current_position = max_pos + (self.current_position % range_size)
            else:
                self.current_position = 0.0
                if self.move_speed < 0:
                    self.move_speed = fabs(self.move_speed)
                    self.reset_animation_timing()
        
        if len(self.move_range) >= 2:
            min_pos = self.move_range[0]
            max_pos = self.move_range[1]
            
            if min_pos > max_pos:
                min_pos, max_pos = max_pos, min_pos
                self.move_range = [int(min_pos), int(max_pos)]
            
            if self.is_edge_reflect:
                if self.current_position <= min_pos:
                    self.current_position = min_pos
                    if self.move_speed < 0:
                        self.move_speed = fabs(self.move_speed)
                        direction_changed = True
                elif self.current_position >= max_pos:
                    self.current_position = max_pos
                    if self.move_speed > 0:
                        self.move_speed = -fabs(self.move_speed)
                        direction_changed = True
                
                if direction_changed:
                    self.reset_animation_timing()
            else:
                range_size = max_pos - min_pos
                if range_size > 0:
                    if self.current_position < min_pos:
                        offset = min_pos - self.current_position
                        self.current_position = max_pos - (offset % range_size)
                    elif self.current_position > max_pos:
                        offset = self.current_position - max_pos
                        self.current_position = min_pos + (offset % range_size)
                else:
                    self.current_position = min_pos
        
        self.current_position = max(-1000.0, self.current_position)
    
    @cython.boundscheck(False)
    def get_led_colors_with_timing_fast(self, int[:, :] palette, double current_time):
        """Get LED colors với Cython optimization"""
        cdef double brightness_factor
        cdef int part_index, part_length, color_index, led_in_part, extra_index
        cdef double transparency
        cdef RGBColor base_color, final_color
        cdef list colors = []
        
        if not self.color or palette.shape[0] == 0:
            return []
        
        brightness_factor = self.get_brightness_at_time(current_time)
        
        if brightness_factor <= 0.0:
            return []
        
        for part_index in range(len(self.length)):
            part_length = max(0, self.length[part_index])
            
            if part_length == 0:
                continue
            
            color_index = self.color[part_index] if part_index < len(self.color) else 0
            transparency = self.transparency[part_index] if part_index < len(self.transparency) else 0.0
            
            if color_index >= 0 and color_index < palette.shape[0]:
                base_color.r = palette[color_index, 0]
                base_color.g = palette[color_index, 1]
                base_color.b = palette[color_index, 2]
            else:
                base_color.r = base_color.g = base_color.b = 0
            
            final_color = apply_transparency_brightness(base_color, transparency, brightness_factor)
            
            for led_in_part in range(part_length):
                colors.append([final_color.r, final_color.g, final_color.b])
        
        if len(self.color) > len(self.length):
            for extra_index in range(len(self.length), len(self.color)):
                color_index = self.color[extra_index]
                transparency = self.transparency[extra_index] if extra_index < len(self.transparency) else 0.0
                
                if color_index >= 0 and color_index < palette.shape[0]:
                    base_color.r = palette[color_index, 0]
                    base_color.g = palette[color_index, 1]
                    base_color.b = palette[color_index, 2]
                else:
                    base_color.r = base_color.g = base_color.b = 0
                
                final_color = apply_transparency_brightness(base_color, transparency, brightness_factor)
                colors.append([final_color.r, final_color.g, final_color.b])
        
        return colors
    
    def get_led_colors_with_timing(self, palette: List[List[int]], current_time: float) -> List[List[int]]:
        """Wrapper method cho compatibility"""
        import numpy as np
        try:
            palette_array = np.array(palette, dtype=np.int32)
            return self.get_led_colors_with_timing_fast(palette_array, current_time)
        except Exception:
            from ..utils.color_utils import ColorUtils
            
            if not self.color or not palette:
                return []
            
            brightness_factor = self.get_brightness_at_time(current_time)
            
            if brightness_factor <= 0.0:
                return []
            
            colors = []
            
            for part_index in range(len(self.length)):
                part_length = max(0, self.length[part_index])
                
                if part_length == 0:
                    continue
                
                color_index = self.color[part_index] if part_index < len(self.color) else 0
                transparency = self.transparency[part_index] if part_index < len(self.transparency) else 0.0
                
                for led_in_part in range(part_length):
                    base_color = ColorUtils.get_palette_color(palette, color_index)
                    
                    final_color = ColorUtils.calculate_segment_color(
                        base_color, transparency, brightness_factor
                    )
                    colors.append(final_color)
            
            if len(self.color) > len(self.length):
                for extra_index in range(len(self.length), len(self.color)):
                    color_index = self.color[extra_index]
                    transparency = self.transparency[extra_index] if extra_index < len(self.transparency) else 0.0
                    
                    base_color = ColorUtils.get_palette_color(palette, color_index)
                    
                    final_color = ColorUtils.calculate_segment_color(
                        base_color, transparency, brightness_factor
                    )
                    colors.append(final_color)
            
            return colors
    
    @cython.boundscheck(False)
    def render_to_led_array_fast(self, int[:, :] palette, double current_time, int[:, :] led_array):
        """Render segment với Cython optimization"""
        cdef double brightness_factor, fractional_part
        cdef int base_position, skip_count, i, led_index, part_index, part_length, color_index, led_in_part, extra_index
        cdef int total_segment_leds = 0
        cdef double transparency
        cdef RGBColor base_color, final_color, faded_color
        cdef RGBColor *segment_colors
        cdef bint is_first, is_last
        
        if not self.color or palette.shape[0] == 0:
            return
        
        brightness_factor = self.get_brightness_at_time(current_time)
        
        if brightness_factor <= 0.0:
            return
        
        segment_colors = <RGBColor*>malloc(1000 * sizeof(RGBColor))
        if segment_colors == NULL:
            return
        
        try:
            for part_index in range(len(self.length)):
                part_length = max(0, self.length[part_index])
                
                if part_length == 0 or total_segment_leds >= 1000:
                    continue
                
                color_index = self.color[part_index] if part_index < len(self.color) else 0
                transparency = self.transparency[part_index] if part_index < len(self.transparency) else 0.0
                
                if color_index >= 0 and color_index < palette.shape[0]:
                    base_color.r = palette[color_index, 0]
                    base_color.g = palette[color_index, 1] 
                    base_color.b = palette[color_index, 2]
                else:
                    base_color.r = base_color.g = base_color.b = 0
                
                final_color = apply_transparency_brightness(base_color, transparency, brightness_factor)
                
                for led_in_part in range(part_length):
                    if total_segment_leds >= 1000:
                        break
                    segment_colors[total_segment_leds] = final_color
                    total_segment_leds += 1
            
            if len(self.color) > len(self.length) and total_segment_leds < 1000:
                for extra_index in range(len(self.length), len(self.color)):
                    if total_segment_leds >= 1000:
                        break
                    
                    color_index = self.color[extra_index]
                    transparency = self.transparency[extra_index] if extra_index < len(self.transparency) else 0.0
                    
                    if color_index >= 0 and color_index < palette.shape[0]:
                        base_color.r = palette[color_index, 0]
                        base_color.g = palette[color_index, 1]
                        base_color.b = palette[color_index, 2]
                    else:
                        base_color.r = base_color.g = base_color.b = 0
                    
                    final_color = apply_transparency_brightness(base_color, transparency, brightness_factor)
                    segment_colors[total_segment_leds] = final_color
                    total_segment_leds += 1
            
            if total_segment_leds > 0:
                if self.current_position < 0 and self.current_position > -total_segment_leds:
                    skip_count = <int>fabs(self.current_position)
                    base_position = 0
                    total_segment_leds -= skip_count
                    for i in range(total_segment_leds):
                        segment_colors[i] = segment_colors[i + skip_count]
                    fractional_part = 0.0
                else:
                    base_position = max(0, <int>self.current_position)
                    fractional_part = max(0.0, min(1.0, self.current_position - base_position))
                
                for i in range(total_segment_leds):
                    led_index = base_position + i
                    
                    if led_index >= 0 and led_index < led_array.shape[0]:
                        faded_color = segment_colors[i]
                        
                        if total_segment_leds > 1 and fractional_part > 0.0:
                            is_first = (i == 0)
                            is_last = (i == total_segment_leds - 1)
                            faded_color = apply_fractional_fade(faded_color, fractional_part, is_first, is_last)
                        
                        add_color_to_led(led_array, led_index, faded_color)
        
        finally:
            free(segment_colors)
    
    def render_to_led_array(self, palette: List[List[int]], current_time: float, 
                           led_array: List[List[int]]) -> None:
        """Render segment với Cython optimization"""
        import numpy as np
        try:
            palette_array = np.array(palette, dtype=np.int32)
            led_array_np = np.array(led_array, dtype=np.int32)
            
            self.render_to_led_array_fast(palette_array, current_time, led_array_np)
            
            for i in range(len(led_array)):
                if i < led_array_np.shape[0]:
                    led_array[i][0] = led_array_np[i, 0]
                    led_array[i][1] = led_array_np[i, 1]
                    led_array[i][2] = led_array_np[i, 2]
            
            return
        except Exception:
            from ..utils.color_utils import ColorUtils
            
            segment_colors = self.get_led_colors_with_timing(palette, current_time)
            
            if not segment_colors:
                return
            
            try:
                if self.current_position < 0:
                    if self.current_position < -len(segment_colors):
                        return
                    
                    skip_count = int(abs(self.current_position))
                    if skip_count >= len(segment_colors):
                        return
                    
                    base_position = 0
                    segment_colors = segment_colors[skip_count:]
                    fractional_part = 0.0
                else:
                    base_position = max(0, int(self.current_position))
                    fractional_part = max(0.0, min(1.0, self.current_position - base_position))
                
                if not led_array or base_position >= len(led_array):
                    return
                
                for i, color in enumerate(segment_colors):
                    led_index = base_position + i
                    
                    if led_index < 0 or led_index >= len(led_array):
                        continue
                    
                    if not isinstance(color, (list, tuple)) or len(color) < 3:
                        continue
                    
                    if len(segment_colors) > 1 and fractional_part > 0:
                        is_first = (i == 0)
                        is_last = (i == len(segment_colors) - 1)
                        faded_color = ColorUtils.calculate_fractional_fade_color(
                            color, fractional_part, is_first, is_last
                        )
                    else:
                        faded_color = ColorUtils.validate_rgb_color(color)
                    
                    ColorUtils.add_colors_to_led_array(led_array, led_index, faded_color)
                            
            except Exception as e:
                import sys
                print(f"Error in render_to_led_array: {e}", file=sys.stderr, flush=True)
    
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
            start_brightness = max(0, min(100, old_format[i]))
            end_brightness = max(0, min(100, old_format[i + 1]))
            new_format.append([default_duration, start_brightness, end_brightness])
        
        return new_format
    
    def reset_position(self):
        """Reset the position to the initial position and restart timing"""
        self.current_position = float(self.initial_position)
        self.reset_animation_timing()
    
    def is_active(self) -> bool:
        """Check if the segment is active"""
        try:
            return (any(c >= 0 for c in self.color) and 
                    sum(max(0, length) for length in self.length) > 0 and
                    any(t > 0 for t in self.transparency))
        except Exception:
            return False
    
    def validate(self) -> bool:
        """Enhanced validation using centralized validation utilities"""
        try:
            if not ValidationUtils.validate_int(self.segment_id, 0, ValidationUtils.MAX_SEGMENT_ID):
                log_validation_error(f"Invalid segment_id: {self.segment_id}", "segment_id")
                return False
            
            if not ValidationUtils.validate_color_indices(self.color):
                log_validation_error(f"Invalid color indices: {self.color}", "color")
                return False
            
            if not ValidationUtils.validate_transparency_values(self.transparency):
                log_validation_error(f"Invalid transparency values: {self.transparency}", "transparency")
                return False
            
            if not ValidationUtils.validate_length_values(self.length):
                log_validation_error(f"Invalid length values: {self.length}", "length")
                return False
            
            if not ValidationUtils.validate_float(self.move_speed, *ValidationUtils.get_speed_range()):
                log_validation_error(f"Invalid move_speed: {self.move_speed}", "move_speed")
                return False
            
            if not ValidationUtils.validate_move_range(self.move_range):
                log_validation_error(f"Invalid move_range: {self.move_range}", "move_range")
                return False
            
            if not ValidationUtils.validate_float(self.current_position, *ValidationUtils.POSITION_RANGE):
                log_validation_error(f"Invalid current_position: {self.current_position}", "current_position")
                return False
            
            if self.dimmer_time and not ValidationUtils.validate_dimmer_time(self.dimmer_time):
                log_validation_error(f"Invalid dimmer_time: {self.dimmer_time}", "dimmer_time")
                return False
            
            if len(self.transparency) != len(self.color) or len(self.length) != len(self.color):
                log_validation_error("Array length mismatch between color, transparency, and length", "array_consistency")
                return False
        
            total_leds = sum(self.length)
            led_range = ValidationUtils.get_default_led_count_range()
            if total_leds > led_range[1]:
                log_validation_error(f"Total LED count {total_leds} exceeds maximum {led_range[1]}", "total_leds")
                return False
            
            return True
            
        except Exception as e:
            AnimationLogger.log_validation_error("segment_validation", str(e), segment_id=self.segment_id)
            return False
    
    def sanitize(self, led_count: int = 225):
        """Sanitize segment data using centralized sanitization utilities"""
        try:
            self.segment_id = DataSanitizer.sanitize_int(self.segment_id, 0, 0, ValidationUtils.MAX_SEGMENT_ID)
            self.color = DataSanitizer.sanitize_color_indices(self.color)
            self.transparency = DataSanitizer.sanitize_transparency_values(self.transparency, len(self.color))
            self.length = DataSanitizer.sanitize_length_values(self.length, len(self.color))
            self.move_speed = DataSanitizer.sanitize_float(self.move_speed, 0.0, *ValidationUtils.get_speed_range())
            self.move_range = DataSanitizer.sanitize_move_range(self.move_range, led_count)
            self.current_position = DataSanitizer.sanitize_float(self.current_position, 0.0, *ValidationUtils.POSITION_RANGE)
            if not self.dimmer_time or not isinstance(self.dimmer_time, list):
                self.dimmer_time = [[1000, 0, 100]]
            else:
                sanitized_dimmer = []
                for transition in self.dimmer_time:
                    if isinstance(transition, list) and len(transition) >= 3:
                        duration = DataSanitizer.sanitize_int(transition[0], 100, 100)
                        start_brightness = DataSanitizer.sanitize_int(transition[1], 0, 0, 100)
                        end_brightness = DataSanitizer.sanitize_int(transition[2], 100, 0, 100)
                        sanitized_dimmer.append([duration, start_brightness, end_brightness])
                
                self.dimmer_time = sanitized_dimmer if sanitized_dimmer else [[1000, 0, 100]]
            
        except Exception as e:
            AnimationLogger.log_validation_error("segment_sanitization", str(e), segment_id=getattr(self, 'segment_id', 0))
            self.segment_id = 0
            self.color = [0]
            self.transparency = [1.0]
            self.length = [1]
            self.move_speed = 0.0
            self.move_range = [0.0, float(max(1, led_count - 1))]
            self.current_position = 0.0
            self.dimmer_time = [[1000, 0, 100]]