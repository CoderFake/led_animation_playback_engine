"""
Comprehensive test cases for dissolve pattern system
Tests dissolve transition logic, timing, validation, and edge cases
"""

import unittest
import time
from unittest.mock import Mock, patch
from src.models.common import DissolveTransition
from src.models.types import DissolvePhase
from src.utils.color_utils import ColorUtils


class TestDissolveTransition(unittest.TestCase):
    """Test dissolve transition functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.led_count = 10
        self.dissolve = DissolveTransition(led_count=self.led_count)
        
    def test_dissolve_initialization(self):
        """Test dissolve transition initialization"""
        self.assertFalse(self.dissolve.is_active)
        self.assertEqual(self.dissolve.phase, DissolvePhase.COMPLETED)
        self.assertEqual(len(self.dissolve.led_states), self.led_count)
        
        # Check initial LED states
        for led_state in self.dissolve.led_states:
            self.assertEqual(led_state['phase'], 'waiting')
            self.assertEqual(led_state['start_time'], 0.0)
            self.assertEqual(led_state['duration_ms'], 0)
            self.assertEqual(led_state['progress'], 0.0)
    
    def test_validate_transition_data_valid(self):
        """Test validation with valid transition data"""
        valid_transitions = [
            [0, 100, 0, 4],      # Basic valid transition
            [500, 200, 2, 7],    # Delayed transition
            [0, 50, 0, 0],       # Single LED
            [100, 300, 5, 9]     # End range
        ]
        
        for transition in valid_transitions:
            with self.subTest(transition=transition):
                self.assertTrue(self.dissolve._validate_transition_data(transition))
    
    def test_validate_transition_data_invalid(self):
        """Test validation with invalid transition data"""
        invalid_transitions = [
            [0, 100, 0],           # Wrong length
            [0, 100, 0, 4, 5],     # Wrong length
            [-100, 100, 0, 4],     # Negative delay
            [0, -100, 0, 4],       # Negative duration
            [0, 0, 0, 4],          # Zero duration
            ["0", 100, 0, 4],      # Wrong type
            [0, 100, 0, 4.5],      # Float LED index (should be int)
        ]
        
        for transition in invalid_transitions:
            with self.subTest(transition=transition):
                self.assertFalse(self.dissolve._validate_transition_data(transition))
    
    def test_setup_led_timing_basic(self):
        """Test basic LED timing setup"""
        pattern_data = [
            [0, 100, 0, 2],      # LEDs 0-2: start immediately, 100ms duration
            [200, 150, 3, 5],    # LEDs 3-5: start after 200ms, 150ms duration
        ]
        
        self.dissolve.start_dissolve(pattern_data, self.led_count)
        
        # Check LEDs 0-2
        for i in range(3):
            led_state = self.dissolve.led_states[i]
            self.assertEqual(led_state['duration_ms'], 100)
            self.assertAlmostEqual(led_state['start_time'], self.dissolve.start_time, places=3)
        
        # Check LEDs 3-5
        for i in range(3, 6):
            led_state = self.dissolve.led_states[i]
            self.assertEqual(led_state['duration_ms'], 150)
            self.assertAlmostEqual(led_state['start_time'], self.dissolve.start_time + 0.2, places=3)
        
        # Check LEDs 6-9 (not in pattern)
        for i in range(6, 10):
            led_state = self.dissolve.led_states[i]
            self.assertEqual(led_state['duration_ms'], 0)
            self.assertEqual(led_state['start_time'], 0.0)
    
    def test_setup_led_timing_overlapping_ranges(self):
        """Test LED timing setup with overlapping ranges - should take earliest timing"""
        pattern_data = [
            [0, 100, 0, 4],      # LEDs 0-4: start immediately
            [50, 200, 2, 6],     # LEDs 2-6: start after 50ms (overlaps with 2-4)
            [25, 150, 3, 5],     # LEDs 3-5: start after 25ms (overlaps with 3-4)
        ]
        
        self.dissolve.start_dissolve(pattern_data, self.led_count)
        
        # LED 0-1: only first transition
        for i in range(2):
            led_state = self.dissolve.led_states[i]
            self.assertEqual(led_state['duration_ms'], 100)
            self.assertAlmostEqual(led_state['start_time'], self.dissolve.start_time, places=3)
        
        # LED 2: first transition (earliest)
        led_state = self.dissolve.led_states[2]
        self.assertEqual(led_state['duration_ms'], 100)
        self.assertAlmostEqual(led_state['start_time'], self.dissolve.start_time, places=3)
        
        # LED 3-4: first transition (earliest, even though third has 25ms)
        for i in range(3, 5):
            led_state = self.dissolve.led_states[i]
            self.assertEqual(led_state['duration_ms'], 100)
            self.assertAlmostEqual(led_state['start_time'], self.dissolve.start_time, places=3)
        
        # LED 5: third transition (25ms, earlier than second's 50ms)
        led_state = self.dissolve.led_states[5]
        self.assertEqual(led_state['duration_ms'], 150)
        self.assertAlmostEqual(led_state['start_time'], self.dissolve.start_time + 0.025, places=3)
        
        # LED 6: second transition only
        led_state = self.dissolve.led_states[6]
        self.assertEqual(led_state['duration_ms'], 200)
        self.assertAlmostEqual(led_state['start_time'], self.dissolve.start_time + 0.05, places=3)
    
    def test_setup_led_timing_boundary_clamping(self):
        """Test LED timing setup with out-of-bounds indices"""
        pattern_data = [
            [0, 100, -5, 2],     # Negative start should clamp to 0
            [100, 200, 8, 15],   # End beyond led_count should clamp to 9
            [200, 150, 12, 20],  # Both out of bounds
        ]
        
        self.dissolve.start_dissolve(pattern_data, self.led_count)
        
        # LEDs 0-2: from first transition (clamped -5 to 0)
        for i in range(3):
            led_state = self.dissolve.led_states[i]
            self.assertEqual(led_state['duration_ms'], 100)
            self.assertAlmostEqual(led_state['start_time'], self.dissolve.start_time, places=3)
        
        # LEDs 8-9: from second transition (clamped 15 to 9)
        for i in range(8, 10):
            led_state = self.dissolve.led_states[i]
            self.assertEqual(led_state['duration_ms'], 200)
            self.assertAlmostEqual(led_state['start_time'], self.dissolve.start_time + 0.1, places=3)
        
        # Third transition should be completely out of bounds, no LEDs affected
    
    def test_update_dissolve_timing(self):
        """Test dissolve update timing logic"""
        pattern_data = [
            [0, 100, 0, 2],      # LEDs 0-2: immediate start, 100ms duration
            [50, 200, 3, 4],     # LEDs 3-4: 50ms delay, 200ms duration
        ]
        
        self.dissolve.start_dissolve(pattern_data, self.led_count)
        
        from_colors = [[255, 0, 0]] * self.led_count  # Red
        to_colors = [[0, 255, 0]] * self.led_count    # Green
        
        # Test at start time
        self.dissolve.update_dissolve(self.dissolve.start_time, from_colors, to_colors)
        
        # LEDs 0-2 should start dissolving immediately
        for i in range(3):
            self.assertEqual(self.dissolve.led_states[i]['phase'], 'dissolving')
            self.assertEqual(self.dissolve.led_states[i]['progress'], 0.0)
        
        # LEDs 3-4 should still be waiting
        for i in range(3, 5):
            self.assertEqual(self.dissolve.led_states[i]['phase'], 'waiting')
        
        # Test at 25ms (middle of first transition)
        current_time = self.dissolve.start_time + 0.025
        self.dissolve.update_dissolve(current_time, from_colors, to_colors)
        
        # LEDs 0-2 should be 25% complete
        for i in range(3):
            self.assertEqual(self.dissolve.led_states[i]['phase'], 'dissolving')
            self.assertAlmostEqual(self.dissolve.led_states[i]['progress'], 0.25, places=2)
        
        # Test at 75ms (after second transition starts)
        current_time = self.dissolve.start_time + 0.075
        self.dissolve.update_dissolve(current_time, from_colors, to_colors)
        
        # LEDs 0-2 should be 75% complete
        for i in range(3):
            self.assertEqual(self.dissolve.led_states[i]['phase'], 'dissolving')
            self.assertAlmostEqual(self.dissolve.led_states[i]['progress'], 0.75, places=2)
        
        # LEDs 3-4 should start dissolving (25ms into their 200ms duration)
        for i in range(3, 5):
            self.assertEqual(self.dissolve.led_states[i]['phase'], 'dissolving')
            self.assertAlmostEqual(self.dissolve.led_states[i]['progress'], 0.125, places=2)
        
        # Test at 150ms (first transition complete, second ongoing)
        current_time = self.dissolve.start_time + 0.15
        self.dissolve.update_dissolve(current_time, from_colors, to_colors)
        
        # LEDs 0-2 should be completed
        for i in range(3):
            self.assertEqual(self.dissolve.led_states[i]['phase'], 'completed')
            self.assertEqual(self.dissolve.led_states[i]['progress'], 1.0)
        
        # LEDs 3-4 should be 50% complete
        for i in range(3, 5):
            self.assertEqual(self.dissolve.led_states[i]['phase'], 'dissolving')
            self.assertAlmostEqual(self.dissolve.led_states[i]['progress'], 0.5, places=2)
    
    def test_get_led_output_phases(self):
        """Test LED output during different dissolve phases"""
        pattern_data = [[0, 100, 0, 2]]
        self.dissolve.start_dissolve(pattern_data, self.led_count)
        
        from_colors = [[255, 0, 0]] * self.led_count  # Red
        to_colors = [[0, 255, 0]] * self.led_count    # Green
        
        # Test waiting phase
        self.dissolve.led_states[0]['phase'] = 'waiting'
        self.dissolve.led_states[1]['phase'] = 'dissolving'
        self.dissolve.led_states[1]['progress'] = 0.5
        self.dissolve.led_states[1]['from_color'] = [255, 0, 0]
        self.dissolve.led_states[1]['to_color'] = [0, 255, 0]
        self.dissolve.led_states[2]['phase'] = 'completed'
        
        output = self.dissolve.get_led_output(from_colors, to_colors)
        
        # LED 0: waiting - should show from_color
        self.assertEqual(output[0], [255, 0, 0])
        
        # LED 1: dissolving at 50% - should show blended color
        expected_blend = ColorUtils.calculate_transition_color([255, 0, 0], [0, 255, 0], 0.5)
        self.assertEqual(output[1], expected_blend)
        
        # LED 2: completed - should show to_color
        self.assertEqual(output[2], [0, 255, 0])
    
    def test_dissolve_completion_detection(self):
        """Test that dissolve properly detects completion"""
        pattern_data = [[0, 100, 0, 1]]
        self.dissolve.start_dissolve(pattern_data, self.led_count)
        
        from_colors = [[255, 0, 0]] * self.led_count
        to_colors = [[0, 255, 0]] * self.led_count
        
        # Initially active
        self.assertTrue(self.dissolve.is_active)
        self.assertEqual(self.dissolve.phase, DissolvePhase.DISSOLVING)
        
        # Update at completion time
        completion_time = self.dissolve.start_time + 0.1  # 100ms
        self.dissolve.update_dissolve(completion_time, from_colors, to_colors)
        
        # Should be completed
        self.assertFalse(self.dissolve.is_active)
        self.assertEqual(self.dissolve.phase, DissolvePhase.COMPLETED)
    
    def test_dissolve_with_empty_pattern(self):
        """Test dissolve behavior with empty pattern"""
        self.dissolve.start_dissolve([], self.led_count)
        
        from_colors = [[255, 0, 0]] * self.led_count
        to_colors = [[0, 255, 0]] * self.led_count
        
        # Should immediately return to_colors
        output = self.dissolve.get_led_output(from_colors, to_colors)
        self.assertEqual(output, to_colors)
    
    def test_dissolve_with_invalid_pattern(self):
        """Test dissolve behavior with invalid pattern data"""
        invalid_pattern = [
            [0, 100, 0, 2],      # Valid
            [-100, 100, 0, 2],   # Invalid: negative delay
            [0, -100, 0, 2],     # Invalid: negative duration
            [0, 100, 5, 2],      # Invalid: start > end
        ]
        
        with patch('src.models.common.logger') as mock_logger:
            self.dissolve.start_dissolve(invalid_pattern, self.led_count)
            
            # Should log warnings for invalid transitions
            self.assertTrue(mock_logger.warning.called)
            
            valid_leds = [0, 1, 2]
            for i in valid_leds:
                self.assertGreater(self.dissolve.led_states[i]['duration_ms'], 0)


if __name__ == '__main__':
    unittest.main() 