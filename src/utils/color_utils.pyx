# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: cdivision=True
# cython: profile=False

"""
ColorUtils tối ưu với Cython - tích hợp trực tiếp
Compile thành bytecode Python, không cần extension riêng biệt
"""

from typing import List, Tuple, Optional
import cython
from cython import Py_ssize_t
from libc.math cimport fabs
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

ctypedef struct RGBColor:
    int r
    int g
    int b

@cython.boundscheck(False)
@cython.wraparound(False)
cdef inline int clamp_rgb(int value) nogil:
    if value < 0:
        return 0
    elif value > 255:
        return 255
    else:
        return value

@cython.boundscheck(False)
@cython.wraparound(False)
cdef inline RGBColor validate_rgb_fast(int r, int g, int b) nogil:
    cdef RGBColor result
    result.r = clamp_rgb(r)
    result.g = clamp_rgb(g)
    result.b = clamp_rgb(b)
    return result

@cython.boundscheck(False)
@cython.wraparound(False)
cdef inline RGBColor apply_transparency_fast(RGBColor base, double transparency) nogil:
    cdef double opacity = 1.0 - transparency
    cdef RGBColor result
    
    if transparency < 0.0:
        opacity = 1.0
    elif transparency > 1.0:
        opacity = 0.0
    
    result.r = <int>(base.r * opacity)
    result.g = <int>(base.g * opacity)
    result.b = <int>(base.b * opacity)
    
    return result

@cython.boundscheck(False)
@cython.wraparound(False)
cdef inline RGBColor apply_brightness_fast(RGBColor color, double brightness_factor) nogil:
    cdef RGBColor result
    
    if brightness_factor < 0.0:
        brightness_factor = 0.0
    elif brightness_factor > 1.0:
        brightness_factor = 1.0
    
    result.r = <int>(color.r * brightness_factor)
    result.g = <int>(color.g * brightness_factor)
    result.b = <int>(color.b * brightness_factor)
    
    return result

@cython.boundscheck(False)
@cython.wraparound(False)
cdef inline RGBColor apply_master_brightness_fast(RGBColor color, int master_brightness) nogil:
    cdef double brightness_factor
    cdef RGBColor result
    
    if master_brightness <= 0:
        result.r = result.g = result.b = 0
        return result
    elif master_brightness >= 255:
        return color
    
    brightness_factor = <double>master_brightness / 255.0
    
    result.r = <int>(color.r * brightness_factor)
    result.g = <int>(color.g * brightness_factor)
    result.b = <int>(color.b * brightness_factor)
    
    return result

@cython.boundscheck(False)
@cython.wraparound(False)
cdef inline RGBColor calculate_transition_fast(RGBColor from_color, RGBColor to_color, double progress) nogil:
    cdef RGBColor result
    cdef double inv_progress
    
    if progress < 0.0:
        progress = 0.0
    elif progress > 1.0:
        progress = 1.0
    
    inv_progress = 1.0 - progress
    
    result.r = <int>(from_color.r * inv_progress + to_color.r * progress)
    result.g = <int>(from_color.g * inv_progress + to_color.g * progress)
    result.b = <int>(from_color.b * inv_progress + to_color.b * progress)
    
    return validate_rgb_fast(result.r, result.g, result.b)

@cython.boundscheck(False)
@cython.wraparound(False)
cdef inline void add_color_to_array_fast(int[:, :] led_array, int index, RGBColor color) nogil:
    if index < 0 or index >= led_array.shape[0]:
        return
    
    led_array[index, 0] = clamp_rgb(led_array[index, 0] + color.r)
    led_array[index, 1] = clamp_rgb(led_array[index, 1] + color.g)
    led_array[index, 2] = clamp_rgb(led_array[index, 2] + color.b)

@cython.boundscheck(False)
@cython.wraparound(False)
cdef inline int count_active_leds_fast(int[:, :] led_array) nogil:
    cdef int count = 0
    cdef int i
    
    for i in range(led_array.shape[0]):
        if led_array[i, 0] > 0 or led_array[i, 1] > 0 or led_array[i, 2] > 0:
            count += 1
    
    return count

@cython.boundscheck(False)
@cython.wraparound(False)
cdef inline void apply_master_brightness_array_fast(int[:, :] led_array, int master_brightness) nogil:
    cdef double brightness_factor
    cdef int i
    cdef RGBColor color, result
    
    if master_brightness <= 0:
        for i in range(led_array.shape[0]):
            led_array[i, 0] = 0
            led_array[i, 1] = 0
            led_array[i, 2] = 0
        return
    elif master_brightness >= 255:
        return
    
    brightness_factor = <double>master_brightness / 255.0
    
    for i in range(led_array.shape[0]):
        color.r = led_array[i, 0]
        color.g = led_array[i, 1]
        color.b = led_array[i, 2]
        
        result = apply_master_brightness_fast(color, master_brightness)
        
        led_array[i, 0] = result.r
        led_array[i, 1] = result.g
        led_array[i, 2] = result.b

class ColorUtils:
    """ColorUtils tối ưu với Cython cho hiệu suất cao"""
    
    @staticmethod
    def validate_rgb_color(color: List[int]) -> List[int]:
        """Validate and sanitize RGB color values"""
        if not isinstance(color, (list, tuple)) or len(color) < 3:
            return [0, 0, 0]
        
        return [max(0, min(255, int(c))) for c in color[:3]]
    
    @staticmethod
    def get_palette_color(palette: List[List[int]], color_index: int) -> List[int]:
        """Get color from palette with validation"""
        if not palette or not (0 <= color_index < len(palette)):
            return [0, 0, 0]
        
        palette_color = palette[color_index]
        if len(palette_color) >= 3:
            return palette_color[:3]
        else:
            return [0, 0, 0]
    
    @staticmethod
    def apply_transparency(base_color: List[int], transparency: float) -> List[int]:
        """Apply transparency to base color"""
        if transparency < 0.0 or transparency > 1.0:
            transparency = max(0.0, min(1.0, transparency))
        
        opacity = 1.0 - transparency
        
        return [int(c * opacity) for c in base_color]
    
    @staticmethod
    def apply_brightness(color: List[int], brightness_factor: float) -> List[int]:
        """Apply brightness factor to color"""
        if brightness_factor < 0.0:
            brightness_factor = 0.0
        elif brightness_factor > 1.0:
            brightness_factor = 1.0
        
        return [int(c * brightness_factor) for c in color]
    
    @staticmethod
    def apply_master_brightness(color: List[int], master_brightness: int) -> List[int]:
        """Apply master brightness (0-255) to color"""
        if master_brightness < 0:
            master_brightness = 0
        elif master_brightness > 255:
            master_brightness = 255
        
        if master_brightness == 255:
            return color
        
        brightness_factor = master_brightness / 255.0
        return [int(c * brightness_factor) for c in color]
    
    @staticmethod
    def apply_fade_factor(color: List[int], fade_factor: float) -> List[int]:
        """Apply fade factor for fractional positioning"""
        if fade_factor < 0.0:
            fade_factor = 0.0
        elif fade_factor > 1.0:
            fade_factor = 1.0
        
        return [int(c * fade_factor) for c in color]
    
    @staticmethod
    def calculate_segment_color(base_color: List[int], transparency: float, brightness_factor: float) -> List[int]:
        """Calculate final segment color with transparency and brightness"""
        validated_color = ColorUtils.validate_rgb_color(base_color)
        color_with_transparency = ColorUtils.apply_transparency(validated_color, transparency)
        final_color = ColorUtils.apply_brightness(color_with_transparency, brightness_factor)
        
        return ColorUtils.validate_rgb_color(final_color)
    
    @staticmethod
    @cython.boundscheck(False)
    def calculate_transition_color_fast(int[:] from_color, int[:] to_color, double progress):
        """Calculate blended color for transitions với Cython optimization"""
        cdef RGBColor from_rgb, to_rgb, result
        
        if from_color.shape[0] < 3 or to_color.shape[0] < 3:
            return [0, 0, 0]
        
        from_rgb.r = from_color[0]
        from_rgb.g = from_color[1] 
        from_rgb.b = from_color[2]
        
        to_rgb.r = to_color[0]
        to_rgb.g = to_color[1]
        to_rgb.b = to_color[2]
        
        result = calculate_transition_fast(from_rgb, to_rgb, progress)
        
        return [result.r, result.g, result.b]
    
    @staticmethod
    def calculate_transition_color(from_color: List[int], to_color: List[int], progress: float) -> List[int]:
        """Calculate blended color for transitions"""
        import numpy as np
        try:
            from_array = np.array(from_color[:3], dtype=np.int32)
            to_array = np.array(to_color[:3], dtype=np.int32)
            return ColorUtils.calculate_transition_color_fast(from_array, to_array, progress)
        except Exception:
            if progress < 0.0:
                progress = 0.0
            elif progress > 1.0:
                progress = 1.0
            
            from_color = ColorUtils.validate_rgb_color(from_color)
            to_color = ColorUtils.validate_rgb_color(to_color)
            
            blended = [
                int(from_color[i] * (1.0 - progress) + to_color[i] * progress)
                for i in range(3)
            ]
            
            return ColorUtils.validate_rgb_color(blended)
    
    @staticmethod
    def calculate_fractional_fade_color(color: List[int], fractional_part: float, is_first: bool, is_last: bool) -> List[int]:
        """Calculate color with fractional positioning fade effect"""
        if len([True for x in [is_first, is_last] if x]) > 1:
            fade_factor = 1.0
        elif is_first:
            fade_factor = max(0.1, fractional_part)
        elif is_last:
            fade_factor = max(0.1, 1.0 - fractional_part)
        else:
            fade_factor = 1.0
        
        return ColorUtils.apply_fade_factor(color, fade_factor)
    
    @staticmethod
    @cython.boundscheck(False)
    def add_colors_to_led_array_fast(int[:, :] led_array, int led_index, int[:] color):
        """Add color to LED array với Cython optimization"""
        cdef RGBColor rgb_color
        
        if color.shape[0] < 3:
            return
        
        rgb_color = validate_rgb_fast(color[0], color[1], color[2])
        add_color_to_array_fast(led_array, led_index, rgb_color)
    
    @staticmethod
    def add_colors_to_led_array(led_array: List[List[int]], led_index: int, color: List[int]) -> None:
        """Add color to LED array with bounds checking and color addition"""
        import numpy as np
        try:
            led_array_np = np.array(led_array, dtype=np.int32)
            color_array = np.array(color[:3], dtype=np.int32)
            ColorUtils.add_colors_to_led_array_fast(led_array_np, led_index, color_array)
            
            if led_index >= 0 and led_index < len(led_array):
                led_array[led_index][0] = led_array_np[led_index, 0]
                led_array[led_index][1] = led_array_np[led_index, 1]
                led_array[led_index][2] = led_array_np[led_index, 2]
        except Exception:
            if led_index < 0 or led_index >= len(led_array):
                return
            
            color = ColorUtils.validate_rgb_color(color)
            
            for j in range(min(3, len(color), len(led_array[led_index]))):
                led_array[led_index][j] = min(255, led_array[led_index][j] + color[j])
    
    @staticmethod
    @cython.boundscheck(False)
    def count_active_leds_fast(int[:, :] led_array):
        """Count LEDs with at least one RGB channel > 0 với Cython optimization"""
        return count_active_leds_fast(led_array)
    
    @staticmethod
    def count_active_leds(led_colors: List[List[int]]) -> int:
        """Count LEDs with at least one RGB channel > 0"""
        import numpy as np
        try:
            led_array = np.array(led_colors, dtype=np.int32)
            return ColorUtils.count_active_leds_fast(led_array)
        except Exception:
            return sum(1 for color in led_colors if any(c > 0 for c in color[:3]))
    
    @staticmethod
    @cython.boundscheck(False)
    def apply_colors_to_array_fast(int[:, :] led_array, int master_brightness):
        """Apply master brightness to entire LED array với Cython optimization"""
        apply_master_brightness_array_fast(led_array, master_brightness)
    
    @staticmethod
    def apply_colors_to_array(led_colors: List[List[int]], master_brightness: int = 255) -> List[List[int]]:
        """Apply master brightness to entire LED array"""
        if master_brightness == 255:
            return led_colors
        
        import numpy as np
        try:
            led_array = np.array(led_colors, dtype=np.int32)
            ColorUtils.apply_colors_to_array_fast(led_array, master_brightness)
            return led_array.tolist()
        except Exception:
            return [
                ColorUtils.apply_master_brightness(color, master_brightness)
                for color in led_colors
            ]