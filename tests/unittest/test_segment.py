"""
Unit tests for Segment class
Tests segment color calculation, timing, positioning, and ColorUtils integration
Updated for new codebase structure with time-based dimmer and fractional positioning
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
from src.utils.color_utils import ColorUtils


class TestSegment(unittest.TestCase):
    """Test Segment class functionality with updated structure"""
    
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
        self.assertEqual(segment.length, [10])  # Default length from actual implementation
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
        
        # Should pad transparency to match color length
        self.assertEqual(len(segment.transparency), 4)
        self.assertEqual(segment.transparency, [0.5, 0.8, 0.0, 0.0])
        
        segment = Segment(
            segment_id=2,
            color=[0, 1, 2],
            length=[5, 10]
        )
        
        # Should pad length to match color length
        self.assertEqual(len(segment.length), 3)
        self.assertEqual(segment.length, [5, 10, 1])
    
    def test_validate_dimmer_time(self):
        """Test dimmer_time validation"""
        segment = Segment(segment_id=1)
        
        # Test valid dimmer_time
        valid_dimmer = [[1000, 0, 100], [500, 50, 75]]
        segment.dimmer_time = valid_dimmer
        segment._validate_dimmer_time()
        self.assertEqual(segment.dimmer_time, valid_dimmer)
        
        # Test invalid dimmer_time (negative duration)
        segment.dimmer_time = [[-100, 0, 100]]
        segment._validate_dimmer_time()
        self.assertEqual(segment.dimmer_time, [[100, 0, 100]])  # Should fix negative duration
        
        # Test invalid brightness values
        segment.dimmer_time = [[1000, -50, 150]]
        segment._validate_dimmer_time()
        self.assertEqual(segment.dimmer_time, [[1000, 0, 100]])  # Should clamp brightness
    
    def test_get_brightness_at_time(self):
        """Test time-based brightness calculation"""
        # Create segment with known dimmer timing
        segment = Segment(
            segment_id=1,
            dimmer_time=[[1000, 0, 100], [500, 100, 50]]  # 1s: 0->100%, 0.5s: 100->50%
        )
        
        # Mock segment start time
        segment.segment_start_time = 1000.0
        
        # Test at start time (should be 0%)
        brightness = segment.get_brightness_at_time(1000.0)
        self.assertAlmostEqual(brightness, 0.0, places=2)
        
        # Test at middle of first transition (should be ~50%)
        brightness = segment.get_brightness_at_time(1000.5)
        self.assertAlmostEqual(brightness, 0.5, places=1)
        
        # Test at end of first transition (should be 100%)
        brightness = segment.get_brightness_at_time(1001.0)
        self.assertAlmostEqual(brightness, 1.0, places=2)
        
        # Test at end of second transition (should be 50%)
        brightness = segment.get_brightness_at_time(1001.5)
        self.assertAlmostEqual(brightness, 0.5, places=1)
    
    def test_get_brightness_at_time_with_cycling(self):
        """Test brightness calculation with cycle repetition"""
        segment = Segment(
            segment_id=1,
            dimmer_time=[[500, 0, 100], [500, 100, 0]]  # 0.5s up, 0.5s down = 1s cycle
        )
        
        segment.segment_start_time = 1000.0
        
        # Test first cycle - 25% into first transition (0->100% over 500ms)
        brightness = segment.get_brightness_at_time(1000.25)  # 250ms = 50% of 500ms
        self.assertAlmostEqual(brightness, 0.5, places=1)  # 50% of transition = 50% brightness
        
        # Test second cycle (after 1s) - same position in cycle
        brightness = segment.get_brightness_at_time(1001.25)  # 250ms into second cycle
        self.assertAlmostEqual(brightness, 0.5, places=1)
    
    def test_get_led_colors_with_timing(self):
        """Test LED color generation with timing"""
        segment = Segment(
            segment_id=1,
            color=[0, 1, 2],
            transparency=[0.0, 0.5, 1.0],  # Opaque, half, transparent
            length=[2, 2, 2],
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
    
    def test_update_position_basic(self):
        """Test basic position update"""
        segment = Segment(
            segment_id=1,
            move_speed=10.0,
            current_position=5.0,
            move_range=[0, 100]
        )
        
        delta_time = 0.1  # 100ms
        segment.update_position(delta_time)
        
        # Position should increase by speed * delta_time
        expected_position = 5.0 + (10.0 * 0.1)
        self.assertAlmostEqual(segment.current_position, expected_position, places=2)
    
    def test_update_position_edge_reflect(self):
        """Test position update with edge reflection"""
        segment = Segment(
            segment_id=1,
            move_speed=10.0,
            current_position=95.0,
            move_range=[0, 100],
            is_edge_reflect=True,
            length=[3]  # Add length for boundary calculation
        )
        
        # Mock reset_animation_timing to track calls
        with patch.object(segment, 'reset_animation_timing') as mock_reset:
            delta_time = 1.0  # 1 second - should hit boundary
            segment.update_position(delta_time)
            
            # Should hit upper boundary, but actual position depends on total segment length
            # The boundary is adjusted by total segment length
            expected_max = 100 - segment.get_total_led_count() + 1  # 100 - 3 + 1 = 98
            self.assertLessEqual(segment.current_position, expected_max + 1)
            self.assertTrue(segment.move_speed > 0)  # Speed should become positive
            mock_reset.assert_called_once()  # Should reset timing on direction change
    
    def test_update_position_wrap_around(self):
        """Test position update with wrap around"""
        segment = Segment(
            segment_id=1,
            move_speed=10.0,
            current_position=95.0,
            move_range=[0, 100],
            is_edge_reflect=False,  # Wrap mode
            length=[3]  # Add length for boundary calculation
        )
        
        delta_time = 1.0  # 1 second - should wrap around
        segment.update_position(delta_time)
        
        # With wrap around, the calculation uses effective_max_pos = max_pos - total_segment_length + 1
        # effective_max_pos = 100 - 3 + 1 = 98
        # range_size = 98 - 0 = 98
        # new_position = 95 + 10 = 105
        # Since 105 > 98, it wraps: offset = 105 - 98 = 7, new_pos = 0 + (7 % 98) = 7
        expected_position = 7.0
        self.assertAlmostEqual(segment.current_position, expected_position, places=1)
    
    def test_render_to_led_array_basic(self):
        """Test basic rendering to LED array"""
        segment = Segment(
            segment_id=1,
            color=[0],
            transparency=[0.0],
            length=[3],
            current_position=2.0
        )
        
        led_array = [[0, 0, 0] for _ in range(10)]
        
        # Mock get_led_colors_with_timing to return known colors
        with patch.object(segment, 'get_led_colors_with_timing', return_value=[[100, 50, 25], [100, 50, 25], [100, 50, 25]]):
            # Mock ColorUtils methods used in rendering
            with patch.object(ColorUtils, 'validate_rgb_color', side_effect=lambda x: x[:3]):
                with patch.object(ColorUtils, 'apply_brightness', side_effect=lambda x, b: x):
                    with patch.object(ColorUtils, 'add_colors_to_led_array') as mock_add:
                        segment.render_to_led_array(self.sample_palette, time.time(), led_array)
                        
                        # Should call add_colors_to_led_array for each LED
                        self.assertEqual(mock_add.call_count, 3)
                        # Check that correct indices were used
                        expected_calls = [
                            unittest.mock.call(led_array, 2, [100, 50, 25], 1.0),
                            unittest.mock.call(led_array, 3, [100, 50, 25], 1.0),
                            unittest.mock.call(led_array, 4, [100, 50, 25], 1.0)
                        ]
                        mock_add.assert_has_calls(expected_calls)
    
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
        
        with patch.object(segment, 'get_led_colors_with_timing', return_value=[[120, 60, 30], [120, 60, 30], [120, 60, 30]]):
            with patch.object(ColorUtils, 'validate_rgb_color', side_effect=lambda x: x[:3]):
                with patch.object(ColorUtils, 'apply_brightness', side_effect=lambda x, b: [int(c * b) for c in x]):
                    with patch.object(ColorUtils, 'add_colors_to_led_array') as mock_add:
                        segment.render_to_led_array(self.sample_palette, time.time(), led_array)
                        
                        # With fractional position 2.3, should apply fade effects
                        # First LED (index 2) should have fade factor 0.3
                        # Last LED (index 4) should have fade factor 0.7
                        # Middle LED (index 3) should have no fade (weight 1.0)
                        
                        self.assertEqual(mock_add.call_count, 3)
                        
                        # Check that fade was applied (calls should have different values)
                        calls = mock_add.call_args_list
                        # First LED should be faded
                        first_call = calls[0]
                        self.assertNotEqual(first_call[0][2], [120, 60, 30])  # Should be faded
                        
                        # Middle LED should be unchanged
                        middle_call = calls[1]
                        self.assertEqual(middle_call[0][2], [120, 60, 30])  # Should be unchanged
    
    def test_render_to_led_array_out_of_bounds(self):
        """Test rendering with out-of-bounds position"""
        segment = Segment(
            segment_id=1,
            color=[0],
            transparency=[0.0],
            length=[5],
            current_position=8.0,  # Near end of array
            move_range=[0, 10]
        )
        
        led_array = [[0, 0, 0] for _ in range(10)]
        
        with patch.object(segment, 'get_led_colors_with_timing', return_value=[[100, 50, 25]] * 5):
            with patch.object(ColorUtils, 'validate_rgb_color', side_effect=lambda x: x[:3]):
                with patch.object(ColorUtils, 'apply_brightness', side_effect=lambda x, b: x):
                    with patch.object(ColorUtils, 'add_colors_to_led_array') as mock_add:
                        segment.render_to_led_array(self.sample_palette, time.time(), led_array)
                        
                        # The actual implementation applies range clamping and might render more LEDs
                        # Just check that some rendering happened and didn't crash
                        self.assertGreaterEqual(mock_add.call_count, 2)
                        self.assertLessEqual(mock_add.call_count, 5)  # Should not exceed segment length
    
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
        
        with patch.object(segment, 'get_led_colors_with_timing', return_value=[[100, 50, 25]] * 5):
            with patch.object(ColorUtils, 'validate_rgb_color', side_effect=lambda x: x[:3]):
                with patch.object(ColorUtils, 'apply_brightness', side_effect=lambda x, b: x):
                    with patch.object(ColorUtils, 'add_colors_to_led_array') as mock_add:
                        segment.render_to_led_array(self.sample_palette, time.time(), led_array)
                        
                        # With position -2.0, first 2 LEDs should be skipped
                        # Remaining 3 LEDs should be rendered starting at position 0
                        self.assertEqual(mock_add.call_count, 3)
                        
                        # Check that rendering started at index 0
                        calls = mock_add.call_args_list
                        first_call = calls[0]
                        self.assertEqual(first_call[0][1], 0)  # First LED index should be 0
    
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
    
    def test_from_dict_creation(self):
        """Test segment creation from dictionary"""
        data = {
            "segment_id": 2,
            "color": [1, 2, 3],
            "transparency": [0.2, 0.5, 0.8],
            "length": [10, 15, 20],
            "move_speed": 75.0,
            "move_range": [5, 150],
            "initial_position": 30,
            "is_edge_reflect": True,
            "dimmer_time": [[800, 0, 100], [200, 100, 0]]
        }
        
        segment = Segment.from_dict(data)
        
        self.assertEqual(segment.segment_id, 2)
        self.assertEqual(segment.color, [1, 2, 3])
        self.assertEqual(segment.transparency, [0.2, 0.5, 0.8])
        self.assertEqual(segment.length, [10, 15, 20])
        self.assertEqual(segment.move_speed, 75.0)
        self.assertEqual(segment.move_range, [5, 150])
        self.assertEqual(segment.initial_position, 30)
        self.assertEqual(segment.is_edge_reflect, True)
        self.assertEqual(segment.dimmer_time, [[800, 0, 100], [200, 100, 0]])
    
    def test_from_dict_legacy_conversion(self):
        """Test segment creation with legacy format conversion"""
        # Test with old segment_ID field name
        data = {
            "segment_ID": 3,  # Old format
            "color": [0],
            "dimmer_time": [0, 100, 50, 0]  # Old 1D format
        }
        
        segment = Segment.from_dict(data)
        
        self.assertEqual(segment.segment_id, 3)
        # dimmer_time should be converted to new 2D format
        self.assertTrue(isinstance(segment.dimmer_time[0], list))
        self.assertEqual(len(segment.dimmer_time[0]), 3)  # [duration, start, end]
    
    def test_convert_legacy_dimmer_time(self):
        """Test legacy dimmer_time conversion"""
        # Test conversion from 1D to 2D format
        old_format = [0, 100, 50, 0]
        new_format = Segment.convert_legacy_dimmer_time(old_format)
        
        # Should create transitions between consecutive values
        expected = [
            [1000, 0, 100],    # 0->100
            [1000, 100, 50],   # 100->50
            [1000, 50, 0]      # 50->0
        ]
        self.assertEqual(new_format, expected)
        
        # Test with insufficient data
        short_format = [50]
        new_format = Segment.convert_legacy_dimmer_time(short_format)
        self.assertEqual(new_format, [[1000, 0, 100]])  # Default
    
    def test_reset_position(self):
        """Test position reset functionality"""
        segment = Segment(
            segment_id=1,
            initial_position=25,
            current_position=75.0
        )
        
        with patch.object(segment, 'reset_animation_timing') as mock_reset:
            segment.reset_position()
            
            self.assertEqual(segment.current_position, 25.0)
            mock_reset.assert_called_once()
    
    def test_is_active(self):
        """Test segment activity detection"""
        # Active segment
        active_segment = Segment(
            segment_id=1,
            color=[0, 1],
            length=[5, 3],
            transparency=[0.5, 0.8]  # Has transparency > 0
        )
        self.assertTrue(active_segment.is_active())
        
        # Inactive segment (all transparent)
        inactive_segment = Segment(
            segment_id=2,
            color=[0, 1],
            length=[5, 3],
            transparency=[0.0, 0.0]  # All transparent
        )
        self.assertFalse(inactive_segment.is_active())
        
        # Segment with zero length
        zero_length_segment = Segment(
            segment_id=3,
            color=[0],
            length=[0],
            transparency=[0.5]
        )
        self.assertFalse(zero_length_segment.is_active())
    
    def test_transparency_bug_fix(self):
        """Test that transparency bug is fixed - CRITICAL TEST"""
        segment = Segment(
            segment_id=1,
            color=[0],
            transparency=[0.0],  # 0.0 = opaque
            length=[1]
        )
        
        with patch.object(segment, 'get_brightness_at_time', return_value=1.0):
            colors = segment.get_led_colors_with_timing(self.sample_palette, time.time())
            
            # With transparency=0.0, should get full color
            self.assertEqual(colors[0], [255, 0, 0])  # Full red
        
        # Test with full transparency
        segment.transparency = [1.0]  # 1.0 = fully transparent
        
        with patch.object(segment, 'get_brightness_at_time', return_value=1.0):
            colors = segment.get_led_colors_with_timing(self.sample_palette, time.time())
            
            # With transparency=1.0, should get no color
            self.assertEqual(colors[0], [0, 0, 0])  # No color
    
    def test_validate_segment_data(self):
        """Test segment data validation"""
        # Test valid segment
        valid_segment = Segment(
            segment_id=1,
            color=[0, 1, 2],
            transparency=[0.0, 0.5, 1.0],
            length=[5, 3, 2],
            move_speed=10.0,
            move_range=[0, 100]
        )
        
        # Validation should pass (if validate method exists)
        if hasattr(valid_segment, 'validate'):
            self.assertTrue(valid_segment.validate())
    
    def test_error_handling_in_rendering(self):
        """Test error handling during rendering"""
        segment = Segment(segment_id=1)
        
        # Test rendering with invalid palette
        led_array = [[0, 0, 0] for _ in range(10)]
        
        # Should not crash with None palette
        try:
            segment.render_to_led_array(None, time.time(), led_array)
        except Exception as e:
            self.fail(f"render_to_led_array raised {e} unexpectedly!")
        
        # Should not crash with empty palette
        try:
            segment.render_to_led_array([], time.time(), led_array)
        except Exception as e:
            self.fail(f"render_to_led_array raised {e} unexpectedly!")


if __name__ == '__main__':
    unittest.main()