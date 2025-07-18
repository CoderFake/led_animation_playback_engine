from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import json
from pathlib import Path
import time

from src.utils.color_utils import ColorUtils
from src.models.types import TransitionPhase, DissolvePhase
from src.utils.logger import ComponentLogger

logger = ComponentLogger("Common")


@dataclass
class EngineStats:
    target_fps: int = 60
    actual_fps: float = 0.0
    frame_count: int = 0
    active_leds: int = 0
    total_leds: int = 225
    animation_time: float = 0.0
    master_brightness: int = 255
    speed_percent: int = 100 
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    animation_running: bool = False


@dataclass
class DissolveTransition:
    """
    Manages active dissolve transition with simultaneous crossfade
    Handles per-LED timing and color blending according to pattern specification
    """
    is_active: bool = False
    phase: DissolvePhase = DissolvePhase.COMPLETED
    
    pattern_data: List[List[int]] = None
    start_time: float = 0.0
    led_count: int = 225
    
    led_states: List[Dict[str, Any]] = None
    from_led_array: List[List[int]] = None
    to_led_array: List[List[int]] = None
    
    def __post_init__(self):
        """Initialize LED states and arrays"""
        if self.led_states is None:
            self.led_states = []
        self._initialize_led_states()
        
        if self.from_led_array is None:
            self.from_led_array = [[0, 0, 0] for _ in range(self.led_count)]
        if self.to_led_array is None:
            self.to_led_array = [[0, 0, 0] for _ in range(self.led_count)]
    
    def _initialize_led_states(self):
        """Initialize per-LED crossfade states"""
        self.led_states = []
        for i in range(self.led_count):
            self.led_states.append({
                'phase': 'waiting',
                'crossfade_start': 0.0,
                'crossfade_duration': 0,
                'crossfade_progress': 0.0,
                'from_color': [0, 0, 0],
                'to_color': [0, 0, 0]
            })
    
    def start_dissolve(self, pattern_data: List[List[int]], led_count: int, 
                    from_led_array: List[List[int]], to_led_array: List[List[int]]):
        """
        Start dissolve transition using pattern timing
        """
        logger.info("start_dissolve called with:")
        logger.info(f"  - pattern_data: {len(pattern_data)} transitions")
        logger.info(f"  - led_count: {led_count}")
        logger.info(f"  - from_led_array: {len(from_led_array)} LEDs")
        logger.info(f"  - to_led_array: {len(to_led_array)} LEDs")
        
        for i, transition in enumerate(pattern_data):
            logger.info(f"  - transition {i}: {transition}")
        
        self.pattern_data = pattern_data
        
        if self.led_count != led_count:
            logger.info(f"Resizing LED count: {self.led_count} → {led_count}")
            self.led_count = led_count
            self._initialize_led_states()
        else:
            self.led_count = led_count
            if not self.led_states or len(self.led_states) != led_count:
                self._initialize_led_states()
        
        self.from_led_array = []
        self.to_led_array = []
        
        for i in range(led_count):
            if i < len(from_led_array):
                self.from_led_array.append(from_led_array[i][:3])
            else:
                self.from_led_array.append([0, 0, 0])
                
            if i < len(to_led_array):
                self.to_led_array.append(to_led_array[i][:3])
            else:
                self.to_led_array.append([0, 0, 0])
        
        logger.info(f"Color arrays prepared: from={len(self.from_led_array)}, to={len(self.to_led_array)}")
        
        self.start_time = time.time()
        
        if not pattern_data:
            logger.warning("Empty pattern data - transition will be instant")
            self.phase = DissolvePhase.COMPLETED
            self.is_active = False
            return
        
        valid_patterns = []
        for i, transition in enumerate(pattern_data):
            logger.info(f"Validating transition {i}: {transition}")
            
            if self._validate_transition_data(transition):
                delay_ms, duration_ms, start_led, end_led = transition
                original_start, original_end = start_led, end_led
                
                start_led = max(0, min(start_led, self.led_count - 1))
                end_led = max(start_led, min(end_led, self.led_count - 1))
                
                logger.info(f"  Original range: {original_start}-{original_end}")
                logger.info(f"  Clamped range: {start_led}-{end_led}")
                logger.info(f"  LED count: {self.led_count}")
                logger.info(f"  Range check: start_led({start_led}) <= end_led({end_led}) < led_count({self.led_count})")
                
                if start_led <= end_led and end_led < self.led_count:
                    valid_patterns.append([delay_ms, duration_ms, start_led, end_led])
                    logger.info(f"  ✓ Valid pattern {i}: {delay_ms}ms delay, {duration_ms}ms duration, LEDs {start_led}-{end_led}")
                else:
                    logger.warning(f"  ✗ Skipping pattern {i}: LED range {start_led}-{end_led} failed range check")
            else:
                logger.warning(f"  ✗ Skipping invalid pattern {i}: validation failed")
        
        logger.info(f"Pattern validation complete: {len(valid_patterns)}/{len(pattern_data)} patterns valid")
        
        if not valid_patterns:
            logger.warning("No valid patterns found - transition will be instant")
            self.phase = DissolvePhase.COMPLETED
            self.is_active = False
            return
        
        self.pattern_data = valid_patterns
        self.phase = DissolvePhase.CROSSFADING
        self.is_active = True
        
        self._setup_crossfade_timing()
        
        logger.info(f"Dissolve started: {self.led_count} LEDs with valid timing")
        logger.info(f"Active: {self.is_active}, Phase: {self.phase}")

    def _setup_crossfade_timing(self):
        """
        Setup crossfade timing for each LED range according to pattern
        """
        if not self.pattern_data:
            logger.warning("No pattern data for timing setup")
            return
        
        logger.info(f"Setting up timing for {len(self.pattern_data)} patterns")
        
        leds_with_timing = 0
        
        for i, transition in enumerate(self.pattern_data):
            delay_ms, duration_ms, start_led, end_led = transition
            
            crossfade_start = self.start_time + (delay_ms / 1000.0)
            crossfade_duration = duration_ms
            
            logger.info(f"Pattern {i}: delay={delay_ms}ms, duration={duration_ms}ms, LEDs={start_led}-{end_led}")
            logger.info(f"  Start time: {crossfade_start:.3f}, Duration: {crossfade_duration}ms")
            
            led_count_for_this_pattern = 0
            for led_idx in range(start_led, end_led + 1):
                if led_idx < len(self.led_states):
                    led_state = self.led_states[led_idx]
                    
                    if led_state['crossfade_start'] == 0.0:
                        led_state['crossfade_start'] = crossfade_start
                        led_state['crossfade_duration'] = crossfade_duration
                        led_state['from_color'] = self.from_led_array[led_idx][:3]
                        led_state['to_color'] = self.to_led_array[led_idx][:3]
                        led_state['phase'] = 'waiting'
                        leds_with_timing += 1
                        led_count_for_this_pattern += 1
                    else:
                        logger.debug(f"    LED {led_idx} already has timing, skipping")
                else:
                    logger.warning(f"    LED {led_idx} out of bounds (max: {len(self.led_states)-1})")
            
            logger.info(f"  Pattern {i} applied to {led_count_for_this_pattern} LEDs")
        
        logger.info(f"Setup complete: {leds_with_timing} LEDs have dissolve timing")
        
        if leds_with_timing == 0:
            logger.warning("No LEDs have timing set - completing immediately")
            self.phase = DissolvePhase.COMPLETED
            self.is_active = False

    def _validate_transition_data(self, transition) -> bool:
        """
        Validate transition data format and values
        Expected format: [delay_ms, duration_ms, start_led, end_led]
        """
        if not isinstance(transition, (list, tuple)) or len(transition) != 4:
            return False
        
        delay_ms, duration_ms, start_led, end_led = transition
        
        if not all(isinstance(x, (int, float)) for x in [delay_ms, duration_ms]):
            return False
        
        if not all(isinstance(x, int) for x in [start_led, end_led]):
            return False
        
        if delay_ms < 0 or duration_ms <= 0:
            return False
        
        return True
    
    def update_dissolve(self, current_time: float) -> List[List[int]]:
        """
        Update crossfade progress and return blended LED array
        
        Args:
            current_time: Current timestamp for timing calculations
            
        Returns:
            Blended LED color array with crossfade applied
        """
        if not self.is_active or self.phase != DissolvePhase.CROSSFADING:
            return self.to_led_array[:self.led_count]
        
        if current_time - self.start_time > 30.0:
            logger.warning("Dissolve transition timeout - forcing completion")
            self.phase = DissolvePhase.COMPLETED
            self.is_active = False
            return self.to_led_array[:self.led_count]
        
        result_array = [[0, 0, 0] for _ in range(self.led_count)]
        active_count = 0
        completed_count = 0
        total_with_timing = 0
        
        for led_idx in range(self.led_count):
            if led_idx >= len(self.led_states):
                result_array[led_idx] = [0, 0, 0]
                continue
                
            led_state = self.led_states[led_idx]
            from_color = led_state['from_color']
            to_color = led_state['to_color']
            
            if led_state['crossfade_start'] == 0.0:
                result_array[led_idx] = to_color[:]
                continue
            
            total_with_timing += 1
            
            if led_state['phase'] == 'waiting':
                if current_time >= led_state['crossfade_start']:
                    led_state['phase'] = 'crossfading'
                    active_count += 1
                else:
                    result_array[led_idx] = from_color[:]
                    active_count += 1
            
            elif led_state['phase'] == 'crossfading':
                elapsed_ms = (current_time - led_state['crossfade_start']) * 1000
                
                if elapsed_ms >= led_state['crossfade_duration']:
                    led_state['phase'] = 'completed'
                    led_state['crossfade_progress'] = 1.0
                    result_array[led_idx] = to_color[:]
                    completed_count += 1
                else:
                    if led_state['crossfade_duration'] > 0:
                        progress = elapsed_ms / led_state['crossfade_duration']
                        progress = min(1.0, max(0.0, progress))
                    else:
                        progress = 1.0
                    
                    led_state['crossfade_progress'] = progress
                    
                    old_factor = 1.0 - progress
                    new_factor = progress
                    
                    result_array[led_idx] = [
                        int(from_color[0] * old_factor + to_color[0] * new_factor),
                        int(from_color[1] * old_factor + to_color[1] * new_factor),
                        int(from_color[2] * old_factor + to_color[2] * new_factor)
                    ]
                    active_count += 1
            
            elif led_state['phase'] == 'completed':
                result_array[led_idx] = to_color[:]
                completed_count += 1
            
            else:
                result_array[led_idx] = to_color[:]
        
        if total_with_timing > 0 and completed_count >= total_with_timing:
            self.phase = DissolvePhase.COMPLETED
            self.is_active = False
            logger.info(f"Dissolve completed: {completed_count}/{total_with_timing} LEDs finished")
        elif active_count == 0 and total_with_timing > 0:
            logger.warning("Force completing dissolve - no active LEDs")
            self.phase = DissolvePhase.COMPLETED
            self.is_active = False
        
        if not hasattr(self, '_debug_frame_count'):
            self._debug_frame_count = 0
        self._debug_frame_count += 1
        
        if self._debug_frame_count % 60 == 0:
            elapsed = current_time - self.start_time
            logger.debug(f"Dissolve progress: {elapsed:.1f}s, active={active_count}, completed={completed_count}/{total_with_timing}")
        
        return result_array