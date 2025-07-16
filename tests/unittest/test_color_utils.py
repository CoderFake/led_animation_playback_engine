"""
Unit tests for ColorUtils class
Tests color calculation functions, transparency logic, brightness application, etc.
"""

import unittest
import sys
import os
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.color_utils import ColorUtils


class TestColorUtils(unittest.TestCase):
    """Test ColorUtils class functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.sample_palette = [
            [255, 0, 0],    # Red
            [0, 255, 0],    # Green  
            [0, 0, 255],    # Blue
            [255, 255, 0],  # Yellow
            [255, 0, 255],  # Magenta
            [0, 255, 255]   # Cyan
        ]
        
        self.sample_colors = [
            [255, 128, 64],
            [100, 200, 150],
            [0, 0, 0],
            [255, 255, 255]
        ]
    
    def test_validate_rgb_color(self):
        """Test RGB color validation"""
        # Valid colors
        self.assertEqual(ColorUtils.validate_rgb_color([255, 128, 64]), [255, 128, 64])
        self.assertEqual(ColorUtils.validate_rgb_color([0, 0, 0]), [0, 0, 0])
        self.assertEqual(ColorUtils.validate_rgb_color([255, 255, 255]), [255, 255, 255])
        
        # Color with extra values (should truncate to 3)
        self.assertEqual(ColorUtils.validate_rgb_color([255, 128, 64, 32]), [255, 128, 64])
        
        # Colors with values out of range (should clamp)
        self.assertEqual(ColorUtils.validate_rgb_color([300, -10, 128]), [255, 0, 128])
        self.assertEqual(ColorUtils.validate_rgb_color([100, 500, -50]), [100, 255, 0])
        
        # Invalid inputs (should return black)
        self.assertEqual(ColorUtils.validate_rgb_color([]), [0, 0, 0])
        self.assertEqual(ColorUtils.validate_rgb_color([255, 128]), [0, 0, 0])
        self.assertEqual(ColorUtils.validate_rgb_color(None), [0, 0, 0])
        self.assertEqual(ColorUtils.validate_rgb_color("invalid"), [0, 0, 0])
    
    def test_get_palette_color(self):
        """Test getting color from palette"""
        # Valid palette indices
        self.assertEqual(ColorUtils.get_palette_color(self.sample_palette, 0), [255, 0, 0])
        self.assertEqual(ColorUtils.get_palette_color(self.sample_palette, 2), [0, 0, 255])
        self.assertEqual(ColorUtils.get_palette_color(self.sample_palette, 5), [0, 255, 255])
        
        # Invalid indices (should return black)
        self.assertEqual(ColorUtils.get_palette_color(self.sample_palette, -1), [0, 0, 0])
        self.assertEqual(ColorUtils.get_palette_color(self.sample_palette, 10), [0, 0, 0])
        
        # Empty or invalid palette
        self.assertEqual(ColorUtils.get_palette_color([], 0), [0, 0, 0])
        self.assertEqual(ColorUtils.get_palette_color(None, 0), [0, 0, 0])
        
        # Palette with invalid color entries
        invalid_palette = [[255, 0], [0, 255, 0, 100]]
        self.assertEqual(ColorUtils.get_palette_color(invalid_palette, 0), [0, 0, 0])
        self.assertEqual(ColorUtils.get_palette_color(invalid_palette, 1), [0, 255, 0])
    
    def test_apply_transparency(self):
        """Test transparency application - CRITICAL BUG FIX TEST"""
        base_color = [255, 128, 64]
        
        # Test correct transparency logic: 0.0 = opaque, 1.0 = transparent
        self.assertEqual(ColorUtils.apply_transparency(base_color, 0.0), [255, 128, 64])  # Fully opaque
        self.assertEqual(ColorUtils.apply_transparency(base_color, 1.0), [0, 0, 0])       # Fully transparent
        
        # Test partial transparency
        result = ColorUtils.apply_transparency([100, 200, 50], 0.5)
        self.assertEqual(result, [50, 100, 25])  # 50% opacity
        
        # Test edge cases
        self.assertEqual(ColorUtils.apply_transparency([255, 255, 255], 0.25), [191, 191, 191])  # 75% opacity
        
        # Test invalid transparency values (should clamp)
        self.assertEqual(ColorUtils.apply_transparency(base_color, -0.5), [255, 128, 64])  # Clamped to 0.0
        self.assertEqual(ColorUtils.apply_transparency(base_color, 1.5), [0, 0, 0])        # Clamped to 1.0
    
    def test_apply_brightness(self):
        """Test brightness factor application"""
        base_color = [255, 128, 64]
        
        # Test normal brightness factors
        self.assertEqual(ColorUtils.apply_brightness(base_color, 1.0), [255, 128, 64])
        self.assertEqual(ColorUtils.apply_brightness(base_color, 0.0), [0, 0, 0])
        self.assertEqual(ColorUtils.apply_brightness(base_color, 0.5), [127, 64, 32])
        
        # Test edge cases
        self.assertEqual(ColorUtils.apply_brightness([100, 200, 50], 0.25), [25, 50, 12])
        
        # Test invalid brightness values (should clamp)
        self.assertEqual(ColorUtils.apply_brightness(base_color, -0.5), [0, 0, 0])        # Clamped to 0.0
        self.assertEqual(ColorUtils.apply_brightness(base_color, 1.5), [255, 128, 64])   # Clamped to 1.0
    
    def test_apply_master_brightness(self):
        """Test master brightness application"""
        base_color = [255, 128, 64]
        
        # Test normal master brightness values
        self.assertEqual(ColorUtils.apply_master_brightness(base_color, 255), [255, 128, 64])  # Full brightness
        self.assertEqual(ColorUtils.apply_master_brightness(base_color, 0), [0, 0, 0])        # No brightness
        self.assertEqual(ColorUtils.apply_master_brightness(base_color, 127), [127, 63, 31])  # Half brightness (127/255)
        
        # Test edge cases
        self.assertEqual(ColorUtils.apply_master_brightness([100, 200, 50], 64), [25, 50, 12])
        
        # Test invalid master brightness values (should clamp)
        self.assertEqual(ColorUtils.apply_master_brightness(base_color, -10), [0, 0, 0])       # Clamped to 0
        self.assertEqual(ColorUtils.apply_master_brightness(base_color, 300), [255, 128, 64])  # Clamped to 255
    
    def test_apply_fade_factor(self):
        """Test fade factor application"""
        base_color = [255, 128, 64]
        
        # Test normal fade factors
        self.assertEqual(ColorUtils.apply_fade_factor(base_color, 1.0), [255, 128, 64])
        self.assertEqual(ColorUtils.apply_fade_factor(base_color, 0.5), [127, 64, 32])
        
        # Test small fade factor
        result = ColorUtils.apply_fade_factor(base_color, 0.05)
        expected = [int(255 * 0.05), int(128 * 0.05), int(64 * 0.05)]
        self.assertEqual(result, expected)
        
        # Test invalid fade factors (should clamp)
        self.assertEqual(ColorUtils.apply_fade_factor(base_color, -0.5), [0, 0, 0])      # Clamped to 0.0
        self.assertEqual(ColorUtils.apply_fade_factor(base_color, 1.5), [255, 128, 64])  # Clamped to 1.0
    
    def test_calculate_segment_color(self):
        """Test complete segment color calculation"""
        base_color = [255, 128, 64]
        
        # Test with no transparency and full brightness
        result = ColorUtils.calculate_segment_color(base_color, 0.0, 1.0)
        self.assertEqual(result, [255, 128, 64])
        
        # Test with transparency and brightness
        result = ColorUtils.calculate_segment_color(base_color, 0.5, 0.8)
        # Expected: apply_transparency first, then brightness (double truncation)
        # Step 1: [255, 128, 64] * (1-0.5) = [127, 64, 32] (truncated)
        # Step 2: [127, 64, 32] * 0.8 = [101, 51, 25] (truncated)
        expected = [101, 51, 25]
        self.assertEqual(result, expected)
        
        # Test with full transparency (should be black)
        result = ColorUtils.calculate_segment_color(base_color, 1.0, 1.0)
        self.assertEqual(result, [0, 0, 0])
        
        # Test with invalid inputs
        result = ColorUtils.calculate_segment_color([300, -10, 128], 0.5, 0.5)
        expected = [int(255 * 0.5 * 0.5), int(0 * 0.5 * 0.5), int(128 * 0.5 * 0.5)]
        self.assertEqual(result, expected)
    
    def test_calculate_transition_color(self):
        """Test transition color blending"""
        from_color = [255, 0, 0]    # Red
        to_color = [0, 255, 0]      # Green
        
        # Test transition progress
        result = ColorUtils.calculate_transition_color(from_color, to_color, 0.0)
        self.assertEqual(result, [255, 0, 0])  # Full from_color
        
        result = ColorUtils.calculate_transition_color(from_color, to_color, 1.0)
        self.assertEqual(result, [0, 255, 0])  # Full to_color
        
        result = ColorUtils.calculate_transition_color(from_color, to_color, 0.5)
        self.assertEqual(result, [127, 127, 0])  # 50% blend
        
        # Test invalid progress values (should clamp)
        result = ColorUtils.calculate_transition_color(from_color, to_color, -0.5)
        self.assertEqual(result, [255, 0, 0])  # Clamped to 0.0
        
        result = ColorUtils.calculate_transition_color(from_color, to_color, 1.5)
        self.assertEqual(result, [0, 255, 0])  # Clamped to 1.0
    
    def test_calculate_fractional_fade_color(self):
        """Test fractional positioning fade effect"""
        base_color = [255, 128, 64]
        fractional_part = 0.3
        
        # Test first LED (fade by fractional_part)
        result = ColorUtils.calculate_fractional_fade_color(base_color, fractional_part, True, False)
        expected = [int(255 * 0.3), int(128 * 0.3), int(64 * 0.3)]
        self.assertEqual(result, expected)
        
        # Test last LED (fade by 1.0 - fractional_part)
        result = ColorUtils.calculate_fractional_fade_color(base_color, fractional_part, False, True)
        expected = [int(255 * 0.7), int(128 * 0.7), int(64 * 0.7)]
        self.assertEqual(result, expected)
        
        # Test middle LED (no fade)
        result = ColorUtils.calculate_fractional_fade_color(base_color, fractional_part, False, False)
        self.assertEqual(result, [255, 128, 64])
        
        # Test single LED (both first and last)
        result = ColorUtils.calculate_fractional_fade_color(base_color, fractional_part, True, True)
        self.assertEqual(result, [255, 128, 64])  # No fade for single LED
    
    def test_add_colors_to_led_array(self):
        """Test adding colors to LED array"""
        led_array = [
            [100, 50, 25],
            [0, 0, 0],
            [200, 100, 50]
        ]
        
        # Test normal addition
        ColorUtils.add_colors_to_led_array(led_array, 1, [50, 100, 25])
        self.assertEqual(led_array[1], [50, 100, 25])
        
        # Test additive blending
        ColorUtils.add_colors_to_led_array(led_array, 0, [50, 100, 25])
        self.assertEqual(led_array[0], [150, 150, 50])
        
        # Test color clamping (should not exceed 255)
        ColorUtils.add_colors_to_led_array(led_array, 2, [100, 200, 250])
        self.assertEqual(led_array[2], [255, 255, 255])
        
        # Test invalid indices (should not crash)
        ColorUtils.add_colors_to_led_array(led_array, -1, [50, 100, 25])
        ColorUtils.add_colors_to_led_array(led_array, 10, [50, 100, 25])
        # Array should remain unchanged for invalid indices
        self.assertEqual(len(led_array), 3)
    
    def test_count_active_leds(self):
        """Test counting active LEDs"""
        led_colors = [
            [255, 128, 64],  # Active
            [0, 0, 0],       # Inactive
            [1, 0, 0],       # Active (R > 0)
            [0, 1, 0],       # Active (G > 0)
            [0, 0, 1],       # Active (B > 0)
            [0, 0, 0]        # Inactive
        ]
        
        active_count = ColorUtils.count_active_leds(led_colors)
        self.assertEqual(active_count, 4)
        
        # Test all inactive
        inactive_colors = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
        active_count = ColorUtils.count_active_leds(inactive_colors)
        self.assertEqual(active_count, 0)
        
        # Test all active
        active_colors = [[255, 255, 255], [100, 100, 100], [1, 1, 1]]
        active_count = ColorUtils.count_active_leds(active_colors)
        self.assertEqual(active_count, 3)
    
    def test_apply_colors_to_array(self):
        """Test applying master brightness to entire array"""
        led_colors = [
            [255, 128, 64],
            [100, 200, 50],
            [0, 0, 0]
        ]
        
        # Test full brightness (should return unchanged)
        result = ColorUtils.apply_colors_to_array(led_colors, 255)
        self.assertEqual(result, led_colors)
        
        # Test half brightness
        result = ColorUtils.apply_colors_to_array(led_colors, 127)
        expected = [
            [127, 63, 31],
            [49, 99, 24],
            [0, 0, 0]
        ]
        self.assertEqual(result, expected)
        
        # Test zero brightness
        result = ColorUtils.apply_colors_to_array(led_colors, 0)
        expected = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
        self.assertEqual(result, expected)


if __name__ == '__main__':
    unittest.main() 