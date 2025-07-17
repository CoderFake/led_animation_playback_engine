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
    dissolve_time: int = 1000
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    animation_running: bool = False


class DissolvePatternManager:
    
    def __init__(self):
        self.patterns: Dict[int, List[List[int]]] = {}
        self.current_pattern_id: int = 0
        self.enabled: bool = True
        
    def load_patterns_from_file(self, file_path: str) -> bool:
        try:
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                logger.error(f"Dissolve pattern file not found: {file_path}")
                return False
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if "dissolve_patterns" not in data:
                logger.error(f"File {file_path} missing 'dissolve_patterns' key")
                return False
            
            patterns_data = data["dissolve_patterns"]
            pattern_keys = list(patterns_data.keys())
            if len(pattern_keys) != len(set(pattern_keys)):
                logger.error("Invalid JSON") 
                return False
            self.patterns.clear()
            
            for pattern_id_str, pattern_data in patterns_data.items():
                try:
                    pattern_id = int(pattern_id_str)
                    if isinstance(pattern_data, list):
                        self.patterns[pattern_id] = pattern_data
                        logger.debug(f"Loaded dissolve pattern {pattern_id}: {len(pattern_data)} transitions")
                    else:
                        logger.warning(f"Invalid pattern data format for pattern {pattern_id}")
                except ValueError:
                    logger.warning(f"Invalid pattern ID: {pattern_id_str}")
                    continue
            
            logger.info(f"Loaded {len(self.patterns)} dissolve patterns from {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading dissolve patterns: {e}")
            return False
    
    def get_pattern(self, pattern_id: int) -> Optional[List[List[int]]]:
        return self.patterns.get(pattern_id)
    
    def set_current_pattern(self, pattern_id: int) -> bool:
        if pattern_id in self.patterns:
            self.current_pattern_id = pattern_id
            logger.info(f"Current dissolve pattern set to {pattern_id}")
            return True
        else:
            logger.warning(f"Dissolve pattern {pattern_id} not found")
            return False
    
    def get_available_patterns(self) -> List[int]:
        return list(self.patterns.keys())


@dataclass
class DissolveTransition:
    """Active dissolve transition state with per-LED timing"""
    is_active: bool = False
    phase: DissolvePhase = DissolvePhase.COMPLETED
    
    from_scene_id: Optional[int] = None
    from_effect_id: Optional[int] = None
    from_palette_id: Optional[int] = None
    to_scene_id: Optional[int] = None
    to_effect_id: Optional[int] = None
    to_palette_id: Optional[int] = None
    
    pattern_id: int = 0
    pattern_data: List[List[int]] = None 
    
    start_time: float = 0.0
    led_count: int = 225
    
    led_states: List[Dict[str, Any]] = None 
    
    def __post_init__(self):
        """Initialize LED states"""
        if self.led_states is None:
            self.led_states = []
        self._initialize_led_states()
    
    def _initialize_led_states(self):
        """Initialize per-LED dissolve states"""
        self.led_states = []
        for i in range(self.led_count):
            self.led_states.append({
                'phase': 'waiting',
                'start_time': 0.0,
                'duration_ms': 0,
                'progress': 0.0,
                'from_color': [0, 0, 0],
                'to_color': [0, 0, 0]
            })
    
    def start_dissolve(self, pattern_data: List[List[int]], led_count: int):
        """Start dissolve transition with dynamic LED count support"""
        self.pattern_data = pattern_data
        
        if self.led_count != led_count:
            self.led_count = led_count
            self._initialize_led_states()
        else:
            self.led_count = led_count
            if not self.led_states or len(self.led_states) != led_count:
                self._initialize_led_states()
        
        self.start_time = time.time()
        
        if not pattern_data:
            self.phase = DissolvePhase.COMPLETED
            self.is_active = False
            return
        
        self.phase = DissolvePhase.DISSOLVING
        self.is_active = True
        
        self._setup_led_timing()

    def _setup_led_timing(self):
        """Setup timing with enhanced validation for large LED counts"""
        if not self.pattern_data:
            return
        
        for transition in self.pattern_data:
            if not self._validate_transition_data(transition):
                continue
                
            delay_ms, duration_ms, start_led, end_led = transition
            
            start_led = max(0, min(start_led, self.led_count - 1))
            end_led = max(start_led, min(end_led, self.led_count - 1))
            
            range_size = end_led - start_led + 1
            if range_size > self.led_count // 2:  
                logger.warning(f"Large dissolve range: {range_size} LEDs ({start_led}-{end_led})")
            
            start_time = self.start_time + (delay_ms / 1000.0)
            
            batch_size = 1000  
            for batch_start in range(start_led, end_led + 1, batch_size):
                batch_end = min(batch_start + batch_size - 1, end_led)
                
                for led_idx in range(batch_start, batch_end + 1):
                    if led_idx < len(self.led_states):
                        led_state = self.led_states[led_idx]
                        
                        if (led_state['start_time'] == 0.0 or 
                            start_time < led_state['start_time']):
                            led_state['start_time'] = start_time
                            led_state['duration_ms'] = duration_ms
                        led_state['phase'] = 'waiting'
    
    def _validate_transition_data(self, transition) -> bool:
        """Validate transition data format and values"""
        if not isinstance(transition, (list, tuple)) or len(transition) != 4:
            logger.warning(f"Invalid transition format: {transition} (expected [delay_ms, duration_ms, start_led, end_led])")
            return False
        
        delay_ms, duration_ms, start_led, end_led = transition
        
        if not all(isinstance(x, (int, float)) for x in [delay_ms, duration_ms]):
            logger.warning(f"Invalid timing data types: delay_ms={delay_ms}, duration_ms={duration_ms}")
            return False
        
        if not all(isinstance(x, int) for x in [start_led, end_led]):
            logger.warning(f"Invalid LED index types: start_led={start_led}, end_led={end_led} (must be integers)")
            return False
        
        if delay_ms < 0:
            logger.warning(f"Invalid delay_ms: {delay_ms} (must be >= 0)")
            return False
        
        if duration_ms <= 0:
            logger.warning(f"Invalid duration_ms: {duration_ms} (must be > 0)")
            return False
        
        return True
    
    def update_dissolve(self, current_time: float, from_colors: List[List[int]], to_colors: List[List[int]]):
        """Update dissolve transition state"""
        if not self.is_active or self.phase != DissolvePhase.DISSOLVING:
            return
        
        all_completed = True
        
        for led_idx in range(min(len(self.led_states), len(from_colors), len(to_colors))):
            led_state = self.led_states[led_idx]
            
            if led_state['phase'] == 'waiting':
                if current_time >= led_state['start_time']:
                    led_state['phase'] = 'dissolving'
                    led_state['from_color'] = from_colors[led_idx][:3]
                    led_state['to_color'] = to_colors[led_idx][:3]
                    elapsed_ms = (current_time - led_state['start_time']) * 1000
                    led_state['progress'] = elapsed_ms / led_state['duration_ms'] if led_state['duration_ms'] > 0 else 1.0
                else:
                    all_completed = False
            
            elif led_state['phase'] == 'dissolving':
                elapsed_ms = (current_time - led_state['start_time']) * 1000
                
                if elapsed_ms >= led_state['duration_ms']:
                    led_state['phase'] = 'completed'
                    led_state['progress'] = 1.0
                else:
                    led_state['progress'] = elapsed_ms / led_state['duration_ms'] if led_state['duration_ms'] > 0 else 1.0
                    all_completed = False
        
        if all_completed:
            self.phase = DissolvePhase.COMPLETED
            self.is_active = False
    
    def get_led_output(self, from_colors: List[List[int]], to_colors: List[List[int]]) -> List[List[int]]:
        """Get blended LED output with array size safety"""
        if not self.is_active or self.phase != DissolvePhase.DISSOLVING:
            return to_colors
        
        min_size = min(len(self.led_states), len(from_colors), len(to_colors), self.led_count)
        if min_size <= 0:
            return to_colors
        
        output = []
        
        for led_idx in range(min_size):
            led_state = self.led_states[led_idx]
            
            from_color = from_colors[led_idx][:3] if led_idx < len(from_colors) and len(from_colors[led_idx]) >= 3 else [0, 0, 0]
            to_color = to_colors[led_idx][:3] if led_idx < len(to_colors) and len(to_colors[led_idx]) >= 3 else [0, 0, 0]
            
            if led_state['phase'] == 'waiting':
                output.append(from_color)
            elif led_state['phase'] == 'dissolving':
                progress = max(0.0, min(1.0, led_state['progress'])) 
                
                if 'from_color' in led_state and 'to_color' in led_state:
                    stored_from = led_state['from_color']
                    stored_to = led_state['to_color']
                else:
                    stored_from = from_color
                    stored_to = to_color
                
                blended = ColorUtils.calculate_transition_color(stored_from, stored_to, progress)
                output.append(blended)
            else: 
                output.append(to_color)
        
        return output

@dataclass  
class PatternTransition:
    """Active pattern transition state"""
    is_active: bool = False
    phase: TransitionPhase = TransitionPhase.COMPLETED
    
    from_effect_id: int = None
    from_palette_id: int = None
    to_effect_id: int = None
    to_palette_id: int = None
    
    start_time: float = 0.0
    fade_in_ms: int = 200
    fade_out_ms: int = 200
    waiting_ms: int = 100
    
    phase_start_time: float = 0.0
    progress: float = 0.0


@dataclass
class PatternTransitionConfig:
    """Configuration for pattern transitions"""
    fade_in_ms: int = 200
    fade_out_ms: int = 200
    waiting_ms: int = 100
