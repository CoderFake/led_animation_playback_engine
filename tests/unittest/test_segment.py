"""
Unit tests for Segment class
Tests segment color calculation, timing, positioning, and ColorUtils integration
"""

import unittest
import sys
import os
import time
from unittest.mock import patch, MagicMock

from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.models.segment import Segment


class TestSegment(unittest.TestCase):
    """Test Segment class functionality"""
    
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
        
        # Basic segment for testing
        self.basic_segment = Segment(
            segment_id=0,
            color=[0, 1, 2],
            transparency=[0.0, 0.5, 1.0],
            length=[5, 3, 2],
            move_speed=0.0,
            move_range=[0, 100],
            initial_position=10,
            dimmer_time=[[1000, 0, 100]]
        )
    
    def test_segment_initialization(self):
        """Test segment initialization and __post_init__"""
        # Test with minimal parameters
        segment = Segment(segment_id=1)
        
        self.assertEqual(segment.segment_id, 1)
        self.assertEqual(segment.color, [0])
        self.assertEqual(segment.transparency, [0.0]) 
        self.assertEqual(segment.length, [10])
        self.assertEqual(segment.move_speed, 0.0)
        self.assertEqual(segment.current_position, 0.0)
        self.assertEqual(segment.dimmer_time, [[1000, 0, 100]])
        
        # Test with full parameters
        segment = Segment(
            segment_id=2,
            color=[1, 2, 3],
            transparency=[0.2, 0.5, 0.8],
            length=[5, 10, 15], 
            initial_position=20
        )
        
        self.assertEqual(segment.color, [1, 2, 3])
        self.assertEqual(segment.transparency, [0.2, 0.5, 0.8])
        self.assertEqual(segment.length, [5, 10, 15])
        self.assertEqual(segment.current_position, 20.0)
    
    def test_segment_data_normalization(self):
        """Test segment data normalization in __post_init__"""
        segment = Segment(
            segment_id=1,
            color=[0, 1, 2, 3],
            transparency=[0.5, 0.8]
        )
        
        self.assertEqual(len(segment.transparency), 4)
        self.assertEqual(segment.transparency, [0.5, 0.8, 0.0, 0.0])
        
        segment = Segment(
            segment_id=2,
            color=[0, 1, 2],
            length=[5, 10]
        )
        
        self.assertEqual(len(segment.length), 3)
        self.assertEqual(segment.length, [5, 10, 1])
    
    def test_get_brightness_at_time(self):
        """Test time-based brightness calculation"""
        # Create segment with known dimmer timing
        segment = Segment(
            segment_id=1,
            dimmer_time=[[1000, 0, 100], [500, 100, 50]]  # 1s: 0->100%, 0.5s: 100->50%
        )
        
        # Mock segment start time
        segment.segment_start_time = 1000.0
        
        # Test at start (should be 0%)
        brightness = segment.get_brightness_at_time(1000.0)
        self.assertAlmostEqual(brightness, 0.0, places=2)  # Start brightness 0%
        
        # Test at middle of first transition (should be ~50%)
        brightness = segment.get_brightness_at_time(1000.5)
        self.assertAlmostEqual(brightness, 0.5, places=1)
        
        # Test at end of first transition (should be 100%)
        brightness = segment.get_brightness_at_time(1001.0)
        self.assertAlmostEqual(brightness, 1.0, places=2)
        
        # Test at end of second transition (should be 50%)
        brightness = segment.get_brightness_at_time(1001.5)  # 1500ms = end of second transition
        # Second transition: 100% -> 50%, at end should be 50%
        self.assertAlmostEqual(brightness, 0.5, places=1)
    
    def test_get_led_colors_with_timing(self):
        """Test LED color generation with timing"""
        segment = Segment(
            segment_id=1,
            color=[0, 1, 2],
            transparency=[0.0, 0.5, 1.0],  # Opaque, half, transparent
            length=[2, 2, 2],  # Original: same length as color
            dimmer_time=[[1000, 100, 100]]  # Constant 100% brightness
        )
        
        with patch.object(segment, 'get_brightness_at_time', return_value=1.0):
            colors = segment.get_led_colors_with_timing(self.sample_palette, time.time())
            
            # Should have 6 LEDs total (2+2+2)
            self.assertEqual(len(colors), 6)
            
            # First 2 LEDs: Red with 0.0 transparency (fully opaque)
            self.assertEqual(colors[0], [255, 0, 0])
            self.assertEqual(colors[1], [255, 0, 0])
            
            # Next 2 LEDs: Green with 0.5 transparency (50% opacity)
            self.assertEqual(colors[2], [0, 127, 0])
            self.assertEqual(colors[3], [0, 127, 0])
            
            # Last 2 LEDs: Blue with 1.0 transparency (fully transparent)
            self.assertEqual(colors[4], [0, 0, 0])
            self.assertEqual(colors[5], [0, 0, 0])
    
    def test_get_led_colors_with_brightness_factor(self):
        """Test LED color generation with brightness factor"""
        segment = Segment(
            segment_id=1,
            color=[0],
            transparency=[0.0],
            length=[3],
            dimmer_time=[[1000, 50, 50]]  # 50% brightness
        )
        
        # Mock brightness to return 0.5
        with patch.object(segment, 'get_brightness_at_time', return_value=0.5):
            colors = segment.get_led_colors_with_timing(self.sample_palette, time.time())
            
            # Should have 3 LEDs with 50% brightness
            self.assertEqual(len(colors), 3)
            for color in colors:
                self.assertEqual(color, [127, 0, 0])  # Red at 50% brightness
    
    def test_get_led_colors_with_zero_brightness(self):
        """Test LED color generation with zero brightness"""
        segment = Segment(
            segment_id=1,
            color=[0, 1, 2],
            transparency=[0.0, 0.0, 0.0],
            length=[2, 2, 2]
        )
        
        # Mock brightness to return 0.0
        with patch.object(segment, 'get_brightness_at_time', return_value=0.0):
            colors = segment.get_led_colors_with_timing(self.sample_palette, time.time())
            
            # Should return empty array when brightness is 0
            self.assertEqual(colors, [])
    
    def test_get_led_colors_with_invalid_palette(self):
        """Test LED color generation with invalid palette"""
        segment = Segment(
            segment_id=1,
            color=[0, 1, 10],  # Index 10 is out of range
            transparency=[0.0, 0.0, 0.0],
            length=[1, 1, 1]
        )
        
        with patch.object(segment, 'get_brightness_at_time', return_value=1.0):
            colors = segment.get_led_colors_with_timing(self.sample_palette, time.time())
            
            # Should have 3 LEDs
            self.assertEqual(len(colors), 3)
            
            # First two should be valid colors
            self.assertEqual(colors[0], [255, 0, 0])  # Red
            self.assertEqual(colors[1], [0, 255, 0])  # Green
            
            # Third should be black (invalid index)
            self.assertEqual(colors[2], [0, 0, 0])
    
    def test_get_led_colors_with_extra_colors(self):
        """Test LED color generation with extra colors beyond length array"""
        segment = Segment(
            segment_id=1,
            color=[0, 1, 2, 3],  # 4 colors
            transparency=[0.0, 0.0, 0.0, 0.0],
            length=[2, 2]  # Only 2 length values
        )
        
        with patch.object(segment, 'get_brightness_at_time', return_value=1.0):
            colors = segment.get_led_colors_with_timing(self.sample_palette, time.time())
            
            # Should have 6 LEDs: 2+2 from length array + 2 extra colors
            self.assertEqual(len(colors), 6)
            
            # First 4 LEDs from length array
            self.assertEqual(colors[0], [255, 0, 0])  # Red
            self.assertEqual(colors[1], [255, 0, 0])  # Red
            self.assertEqual(colors[2], [0, 255, 0])  # Green
            self.assertEqual(colors[3], [0, 255, 0])  # Green
            
            # Extra 2 LEDs from extra colors
            self.assertEqual(colors[4], [0, 0, 255])    # Blue
            self.assertEqual(colors[5], [255, 255, 0])  # Yellow
    
    def test_render_to_led_array_basic(self):
        """Test basic rendering to LED array"""
        segment = Segment(
            segment_id=1,
            color=[0],
            transparency=[0.0],
            length=[3],
            initial_position=2,
            current_position=2.0
        )
        
        # Create LED array
        led_array = [[0, 0, 0] for _ in range(10)]
        
        # Mock get_led_colors_with_timing to return known colors
        with patch.object(segment, 'get_led_colors_with_timing', return_value=[[100, 50, 25], [100, 50, 25], [100, 50, 25]]):
            segment.render_to_led_array(self.sample_palette, time.time(), led_array)
            
            # Check that colors were added to correct positions
            self.assertEqual(led_array[2], [100, 50, 25])
            self.assertEqual(led_array[3], [100, 50, 25])
            self.assertEqual(led_array[4], [100, 50, 25])
            
            # Other positions should remain unchanged
            self.assertEqual(led_array[0], [0, 0, 0])
            self.assertEqual(led_array[1], [0, 0, 0])
            self.assertEqual(led_array[5], [0, 0, 0])
    
    def test_render_to_led_array_fractional_position(self):
        """Test rendering with fractional positioning"""
        segment = Segment(
            segment_id=1,
            color=[0],
            transparency=[0.0],
            length=[3],
            current_position=2.3  # Fractional position
        )
        
        led_array = [[0, 0, 0] for _ in range(10)]
        
        # Mock get_led_colors_with_timing to return known colors
        with patch.object(segment, 'get_led_colors_with_timing', return_value=[[120, 60, 30], [120, 60, 30], [120, 60, 30]]):
            segment.render_to_led_array(self.sample_palette, time.time(), led_array)
            
            # With fractional position 2.3, should apply fade effects
            # First LED (index 2) should have fade factor 0.3
            # Last LED (index 4) should have fade factor 0.7
            # Middle LED (index 3) should have no fade
            
            # Check that colors were modified by fractional positioning
            self.assertNotEqual(led_array[2], [120, 60, 30])  # Should be faded
            self.assertEqual(led_array[3], [120, 60, 30])     # Should be unchanged
            self.assertNotEqual(led_array[4], [120, 60, 30])  # Should be faded
    
    def test_render_to_led_array_negative_position(self):
        """Test rendering with negative position"""
        segment = Segment(
            segment_id=1,
            color=[0],
            transparency=[0.0],
            length=[5],
            current_position=-2.0  # Negative position
        )
        
        led_array = [[0, 0, 0] for _ in range(10)]
        
        # Mock get_led_colors_with_timing to return known colors
        with patch.object(segment, 'get_led_colors_with_timing', return_value=[[100, 50, 25], [100, 50, 25], [100, 50, 25], [100, 50, 25], [100, 50, 25]]):
            segment.render_to_led_array(self.sample_palette, time.time(), led_array)
            
            # With position -2.0, first 2 LEDs should be skipped
            # Remaining 3 LEDs should be rendered starting at position 0
            self.assertEqual(led_array[0], [100, 50, 25])
            self.assertEqual(led_array[1], [100, 50, 25])
            self.assertEqual(led_array[2], [100, 50, 25])
            self.assertEqual(led_array[3], [0, 0, 0])  # Should remain unchanged
    
    def test_render_to_led_array_out_of_bounds(self):
        """Test rendering with out-of-bounds position"""
        segment = Segment(
            segment_id=1,
            color=[0],
            transparency=[0.0],
            length=[3],
            current_position=8.0  # Near end of array
        )
        
        led_array = [[0, 0, 0] for _ in range(10)]
        
        # Mock get_led_colors_with_timing to return known colors
        with patch.object(segment, 'get_led_colors_with_timing', return_value=[[100, 50, 25], [100, 50, 25], [100, 50, 25]]):
            segment.render_to_led_array(self.sample_palette, time.time(), led_array)
            
            # Only LEDs within bounds should be rendered
            self.assertEqual(led_array[8], [100, 50, 25])
            self.assertEqual(led_array[9], [100, 50, 25])
            # Position 10 would be out of bounds, so not rendered
    
    def test_render_to_led_array_additive_blending(self):
        """Test additive color blending in LED array"""
        segment = Segment(
            segment_id=1,
            color=[0],
            transparency=[0.0],
            length=[2],
            current_position=2.0
        )
        
        # Pre-populate LED array with existing colors
        led_array = [[50, 25, 10] for _ in range(10)]
        
        # Mock get_led_colors_with_timing to return known colors
        with patch.object(segment, 'get_led_colors_with_timing', return_value=[[100, 50, 25], [100, 50, 25]]):
            segment.render_to_led_array(self.sample_palette, time.time(), led_array)
            
            # Colors should be added to existing values
            self.assertEqual(led_array[2], [150, 75, 35])  # 50+100, 25+50, 10+25
            self.assertEqual(led_array[3], [150, 75, 35])
            
            # Other positions should remain unchanged
            self.assertEqual(led_array[0], [50, 25, 10])
            self.assertEqual(led_array[1], [50, 25, 10])
    
    def test_render_to_led_array_color_clamping(self):
        """Test color value clamping in LED array"""
        segment = Segment(
            segment_id=1,
            color=[0],
            transparency=[0.0],
            length=[2],
            current_position=2.0
        )
        
        # Pre-populate LED array with high values
        led_array = [[200, 200, 200] for _ in range(10)]
        
        # Mock get_led_colors_with_timing to return high colors
        with patch.object(segment, 'get_led_colors_with_timing', return_value=[[100, 100, 100], [100, 100, 100]]):
            segment.render_to_led_array(self.sample_palette, time.time(), led_array)
            
            # Colors should be clamped to 255
            self.assertEqual(led_array[2], [255, 255, 255])
            self.assertEqual(led_array[3], [255, 255, 255])
    
    def test_get_total_led_count(self):
        """Test total LED count calculation"""
        # Test basic count
        segment = Segment(
            segment_id=1,
            color=[0, 1, 2],
            length=[5, 3, 2]
        )
        
        total = segment.get_total_led_count()
        self.assertEqual(total, 10)  # 5+3+2
        
        # Test with extra colors
        segment = Segment(
            segment_id=2,
            color=[0, 1, 2, 3, 4],  # 5 colors
            length=[5, 3]  # Only 2 length values
        )
        
        total = segment.get_total_led_count()
        self.assertEqual(total, 11)  # 5+3 + 3 extra colors
        
        # Test with zero lengths
        segment = Segment(
            segment_id=3,
            color=[0, 1, 2],
            length=[0, 5, 0] 
        )
        
        total = segment.get_total_led_count()
        self.assertEqual(total, 5)  # Only middle segment counts
    
    def test_to_dict_serialization(self):
        """Test segment serialization to dictionary"""
        segment = Segment(
            segment_id=1,
            color=[0, 1, 2],
            transparency=[0.0, 0.5, 1.0],
            length=[5, 3, 2],
            move_speed=50.0,
            move_range=[10, 200],
            initial_position=25,
            is_edge_reflect=False,
            dimmer_time=[[1000, 0, 100], [500, 100, 50]]
        )
        
        segment_dict = segment.to_dict()
        
        # Check all fields are present
        self.assertEqual(segment_dict['segment_id'], 1)
        self.assertEqual(segment_dict['color'], [0, 1, 2])
        self.assertEqual(segment_dict['transparency'], [0.0, 0.5, 1.0])
        self.assertEqual(segment_dict['length'], [5, 3, 2])
        self.assertEqual(segment_dict['move_speed'], 50.0)
        self.assertEqual(segment_dict['move_range'], [10, 200])
        self.assertEqual(segment_dict['initial_position'], 25)
        self.assertEqual(segment_dict['is_edge_reflect'], False)
        self.assertEqual(segment_dict['dimmer_time'], [[1000, 0, 100], [500, 100, 50]])
    
    def test_transparency_bug_fix(self):
        """Test that transparency bug is fixed - CRITICAL TEST"""
        segment = Segment(
            segment_id=1,
            color=[0],
            transparency=[0.0],
            length=[1]
        )
        
        with patch.object(segment, 'get_brightness_at_time', return_value=1.0):
            colors = segment.get_led_colors_with_timing(self.sample_palette, time.time())
            
            # With transparency=0.0, should get full color
            self.assertEqual(colors[0], [255, 0, 0])  # Full red
        
        # Test with full transparency
        segment.transparency = [1.0]  # Should be fully transparent
        
        with patch.object(segment, 'get_brightness_at_time', return_value=1.0):
            colors = segment.get_led_colors_with_timing(self.sample_palette, time.time())
            
            # With transparency=1.0, should get no color
            self.assertEqual(colors[0], [0, 0, 0])  # No color


if __name__ == '__main__':
    unittest.main() 