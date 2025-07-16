"""
Color calculation utilities - Centralized color processing functions
Handles transparency, brightness, fade effects, and master brightness consistently
"""

from typing import List, Tuple, Optional
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class ColorUtils:
    """Centralized color calculation utilities following DRY principles"""
    
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
        """
        Apply transparency to base color
        transparency: 0.0 = opaque (full color), 1.0 = transparent (no color)
        """
        if transparency < 0.0 or transparency > 1.0:
            logger.warning(f"Invalid transparency {transparency}, clamping to [0.0, 1.0]")
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
        """
        Calculate final segment color with transparency and brightness
        """
        validated_color = ColorUtils.validate_rgb_color(base_color)
        color_with_transparency = ColorUtils.apply_transparency(validated_color, transparency)
        final_color = ColorUtils.apply_brightness(color_with_transparency, brightness_factor)
        
        return ColorUtils.validate_rgb_color(final_color)
    
    @staticmethod
    def calculate_transition_color(from_color: List[int], to_color: List[int], progress: float) -> List[int]:
        """Calculate blended color for transitions"""
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
        """
        Calculate color with fractional positioning fade effect
        is_first: LED đầu tiên trong segment
        is_last: LED cuối cùng trong segment
        """
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
    def add_colors_to_led_array(led_array: List[List[int]], led_index: int, color: List[int]) -> None:
        """
        Add color to LED array with bounds checking and color addition
        """
        if led_index < 0 or led_index >= len(led_array):
            return
        
        color = ColorUtils.validate_rgb_color(color)
        
        for j in range(min(3, len(color), len(led_array[led_index]))):
            led_array[led_index][j] = min(255, led_array[led_index][j] + color[j])
    
    @staticmethod
    def count_active_leds(led_colors: List[List[int]]) -> int:
        """Count LEDs with at least one RGB channel > 0"""
        return sum(1 for color in led_colors if any(c > 0 for c in color[:3]))
    
    @staticmethod
    def apply_colors_to_array(led_colors: List[List[int]], master_brightness: int = 255) -> List[List[int]]:
        """
        Apply master brightness to entire LED array
        """
        if master_brightness == 255:
            return led_colors
        
        return [
            ColorUtils.apply_master_brightness(color, master_brightness)
            for color in led_colors
        ]

 