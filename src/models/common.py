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
        
        Args:
            pattern_data: List of [delay_ms, duration_ms, start_led, end_led] transitions
            led_count: Number of LEDs in the array
            from_led_array: Current LED colors (source)
            to_led_array: Target LED colors (destination)
        """
        self.pattern_data = pattern_data
        
        if self.led_count != led_count:
            self.led_count = led_count
            self._initialize_led_states()
        else:
            self.led_count = led_count
            if not self.led_states or len(self.led_states) != led_count:
                self._initialize_led_states()
        
        self.from_led_array = [color[:3] for color in from_led_array]
        self.to_led_array = [color[:3] for color in to_led_array]
        
        while len(self.from_led_array) < self.led_count:
            self.from_led_array.append([0, 0, 0])
        while len(self.to_led_array) < self.led_count:
            self.to_led_array.append([0, 0, 0])
        
        self.start_time = time.time()
        
        if not pattern_data:
            logger.warning("Empty pattern data - transition will be instant")
            self.phase = DissolvePhase.COMPLETED
            self.is_active = False
            return
        
        self.phase = DissolvePhase.CROSSFADING
        self.is_active = True
        
        self._setup_crossfade_timing()
        logger.info(f"Started dissolve transition with {len(pattern_data)} timing groups")

    def _setup_crossfade_timing(self):
        """
        Setup crossfade timing for each LED range according to pattern
        Each transition: [delay_ms, duration_ms, start_led, end_led]
        """
        if not self.pattern_data:
            return
        
        valid_transitions = 0
        for transition in self.pattern_data:
            if not self._validate_transition_data(transition):
                logger.warning(f"Skipping invalid transition: {transition}")
                continue
                
            delay_ms, duration_ms, start_led, end_led = transition
            
            start_led = max(0, min(start_led, self.led_count - 1))
            end_led = max(start_led, min(end_led, self.led_count - 1))
            
            crossfade_start = self.start_time + (delay_ms / 1000.0)
            crossfade_duration = duration_ms
            
            for led_idx in range(start_led, end_led + 1):
                if led_idx < len(self.led_states):
                    led_state = self.led_states[led_idx]
                    
                    if led_state['crossfade_start'] == 0.0:
                        led_state['crossfade_start'] = crossfade_start
                        led_state['crossfade_duration'] = crossfade_duration
                        led_state['from_color'] = self.from_led_array[led_idx][:3]
                        led_state['to_color'] = self.to_led_array[led_idx][:3]
                        led_state['phase'] = 'waiting'
            
            valid_transitions += 1
            
        logger.debug(f"Applied {valid_transitions} valid transitions to LED ranges")
    
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
            return self.to_led_array
        
        result_array = [[0, 0, 0] for _ in range(self.led_count)]
        all_completed = True
        
        for led_idx in range(self.led_count):
            led_state = self.led_states[led_idx]
            from_color = led_state['from_color']
            to_color = led_state['to_color']
            
            if led_state['phase'] == 'waiting':
                if current_time >= led_state['crossfade_start']:
                    led_state['phase'] = 'crossfading'
                    all_completed = False
                else:
                    result_array[led_idx] = from_color[:]
                    all_completed = False
            
            elif led_state['phase'] == 'crossfading':
                elapsed_ms = (current_time - led_state['crossfade_start']) * 1000
                
                if elapsed_ms >= led_state['crossfade_duration']:
                    led_state['phase'] = 'completed'
                    led_state['crossfade_progress'] = 1.0
                    result_array[led_idx] = to_color[:]
                else:
                    progress = elapsed_ms / led_state['crossfade_duration']
                    led_state['crossfade_progress'] = min(1.0, max(0.0, progress))
                    
                    old_factor = 1.0 - led_state['crossfade_progress']
                    new_factor = led_state['crossfade_progress']
                    
                    result_array[led_idx] = [
                        int(from_color[0] * old_factor + to_color[0] * new_factor),
                        int(from_color[1] * old_factor + to_color[1] * new_factor),
                        int(from_color[2] * old_factor + to_color[2] * new_factor)
                    ]
                    all_completed = False
            
            elif led_state['phase'] == 'completed':
                result_array[led_idx] = to_color[:]
            
            else:
                result_array[led_idx] = to_color[:]
        
        if all_completed:
            self.phase = DissolvePhase.COMPLETED
            self.is_active = False
            logger.debug("Dissolve transition completed")
        
        return result_array