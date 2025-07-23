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
    """Test ColorUtils class functionality with updated methods"""
    
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
    
    def test_clamp_color_value(self):
        """Test single color value clamping"""
        self.assertEqual(ColorUtils.clamp_color_value(255), 255)
        self.assertEqual(ColorUtils.clamp_color_value(0), 0)
        self.assertEqual(ColorUtils.clamp_color_value(-10), 0)
        self.assertEqual(ColorUtils.clamp_color_value(300), 255)
        self.assertEqual(ColorUtils.clamp_color_value(128), 128)
    
    def test_clamp_color(self):
        """Test RGB color clamping"""
        self.assertEqual(ColorUtils.clamp_color([255, 128, 64]), [255, 128, 64])
        self.assertEqual(ColorUtils.clamp_color([300, -10, 128]), [255, 0, 128])
        self.assertEqual(ColorUtils.clamp_color([100, 500, -50]), [100, 255, 0])
        self.assertEqual(ColorUtils.clamp_color([0, 0, 0]), [0, 0, 0])
    
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
    
    def test_calculate_segment_color(self):
        """Test complete segment color calculation"""
        base_color = [255, 128, 64]
        
        # Test with no transparency and full brightness
        result = ColorUtils.calculate_segment_color(base_color, 0.0, 1.0)
        self.assertEqual(result, [255, 128, 64])
        
        # Test with transparency and brightness
        result = ColorUtils.calculate_segment_color(base_color, 0.5, 0.8)
        # Expected: apply_transparency first, then brightness
        # Step 1: [255, 128, 64] * (1-0.5) = [127, 64, 32]
        # Step 2: [127, 64, 32] * 0.8 = [101, 51, 25]
        expected = [101, 51, 25]
        self.assertEqual(result, expected)
        
        # Test with full transparency (should be black)
        result = ColorUtils.calculate_segment_color(base_color, 1.0, 1.0)
        self.assertEqual(result, [0, 0, 0])
        
        # Test with invalid inputs (should clamp)
        result = ColorUtils.calculate_segment_color([300, -10, 128], 0.5, 0.5)
        # First clamp to [255, 0, 128], then apply transparency and brightness
        expected = [int(255 * 0.5 * 0.5), int(0 * 0.5 * 0.5), int(128 * 0.5 * 0.5)]
        self.assertEqual(result, expected)
    
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
    
    def test_reset_frame_contributions(self):
        """Test frame contributions reset"""
        # Add some contributions first
        ColorUtils._led_contributions = {0: [([255, 0, 0], 1.0)], 1: [([0, 255, 0], 0.5)]}
        
        # Reset should clear all contributions
        ColorUtils.reset_frame_contributions()
        self.assertEqual(len(ColorUtils._led_contributions), 0)
    
    def test_add_colors_to_led_array_single_contribution(self):
        """Test adding single color contribution to LED array"""
        ColorUtils.reset_frame_contributions()
        led_array = [[0, 0, 0] for _ in range(5)]
        
        # Add single contribution
        ColorUtils.add_colors_to_led_array(led_array, 1, [255, 128, 64], 1.0)
        
        # Finalize should apply the single contribution directly
        ColorUtils.finalize_frame_blending(led_array)
        
        self.assertEqual(led_array[1], [255, 128, 64])
        self.assertEqual(led_array[0], [0, 0, 0])  # Unchanged
        self.assertEqual(led_array[2], [0, 0, 0])  # Unchanged
    
    def test_add_colors_to_led_array_multiple_contributions(self):
        """Test adding multiple color contributions for averaging"""
        ColorUtils.reset_frame_contributions()
        led_array = [[0, 0, 0] for _ in range(5)]
        
        # Add multiple contributions to same LED
        ColorUtils.add_colors_to_led_array(led_array, 1, [255, 0, 0], 1.0)    # Red, weight 1.0
        ColorUtils.add_colors_to_led_array(led_array, 1, [0, 255, 0], 1.0)    # Green, weight 1.0
        
        # Finalize should average the contributions
        ColorUtils.finalize_frame_blending(led_array)
        
        # Expected: (255*1.0 + 0*1.0)/(1.0+1.0) = 127 for R
        #           (0*1.0 + 255*1.0)/(1.0+1.0) = 127 for G
        #           (0*1.0 + 0*1.0)/(1.0+1.0) = 0 for B
        self.assertEqual(led_array[1], [127, 127, 0])
    
    def test_add_colors_to_led_array_weighted_contributions(self):
        """Test weighted color contributions"""
        ColorUtils.reset_frame_contributions()
        led_array = [[0, 0, 0] for _ in range(5)]
        
        # Add weighted contributions
        ColorUtils.add_colors_to_led_array(led_array, 2, [255, 0, 0], 0.3)    # Red, weight 0.3
        ColorUtils.add_colors_to_led_array(led_array, 2, [0, 255, 0], 0.7)    # Green, weight 0.7
        
        # Finalize should apply weighted average
        ColorUtils.finalize_frame_blending(led_array)
        
        # Expected: (255*0.3 + 0*0.7)/(0.3+0.7) = 76 for R
        #           (0*0.3 + 255*0.7)/(0.3+0.7) = 178 for G
        #           (0*0.3 + 0*0.7)/(0.3+0.7) = 0 for B
        self.assertEqual(led_array[2], [76, 178, 0])
    
    def test_add_colors_to_led_array_out_of_bounds(self):
        """Test adding colors with out-of-bounds indices"""
        ColorUtils.reset_frame_contributions()
        led_array = [[0, 0, 0] for _ in range(3)]
        
        # Try to add to invalid indices
        ColorUtils.add_colors_to_led_array(led_array, -1, [255, 0, 0])
        ColorUtils.add_colors_to_led_array(led_array, 5, [0, 255, 0])
        
        # Should not crash and array should remain unchanged
        ColorUtils.finalize_frame_blending(led_array)
        
        for color in led_array:
            self.assertEqual(color, [0, 0, 0])
    
    def test_finalize_frame_blending_zero_weight(self):
        """Test finalize with zero total weight"""
        ColorUtils.reset_frame_contributions()
        led_array = [[100, 100, 100] for _ in range(3)]
        
        # Manually add contribution with zero weight
        ColorUtils._led_contributions[1] = [([255, 0, 0], 0.0)]
        
        # Should handle zero weight gracefully
        ColorUtils.finalize_frame_blending(led_array)
        
        # Should result in black due to zero weight
        self.assertEqual(led_array[1], [0, 0, 0])


if __name__ == '__main__':
    unittest.main()