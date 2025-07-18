"""
Common models for LED Animation Engine with Dual Pattern Dissolve System
Handles simultaneous fade-out and fade-in of two patterns
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import time
import threading

from src.utils.color_utils import ColorUtils
from src.models.types import DissolvePhase
from src.utils.logger import ComponentLogger

logger = ComponentLogger("Common")


@dataclass
class EngineStats:
    """Engine performance and status statistics"""
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
class PatternState:
    """
    Represents a pattern state during dissolve transition
    Pattern = Effect + Palette + Scene combination
    """
    scene_id: int
    effect_id: int
    palette_id: int


@dataclass
class LEDCrossfadeState:
    """
    Per-LED crossfade state for dual pattern dissolve
    Each LED has independent timing and blends two patterns simultaneously
    """
    crossfade_start_time: float = 0.0
    crossfade_duration_ms: int = 0
    blend_progress: float = 0.0


@dataclass
class FPSAdjustment:
    """FPS adjustment event data"""
    old_target: float
    new_target: float
    reason: str
    led_count: int
    avg_processing_time: float

class DualPatternCalculator:
    """
    Calculates LED colors for dual pattern system during dissolve
    Renders both patterns simultaneously and blends them according to per-LED timing
    """
    
    def __init__(self, scene_manager):
        self.scene_manager = scene_manager
        self._lock = threading.RLock()
        
    def calculate_pattern_colors(self, pattern_state: PatternState, current_time: float, 
                                led_count: int) -> List[List[int]]:
        """
        Calculate LED colors for a specific pattern with animation continuing
        
        Args:
            pattern_state: Pattern configuration (scene, effect, palette)
            current_time: Current timestamp for animation timing
            led_count: Number of LEDs to calculate
            
        Returns:
            List of RGB color arrays for each LED
        """
        try:
            with self._lock:
                if pattern_state.scene_id not in self.scene_manager.scenes:
                    return [[0, 0, 0] for _ in range(led_count)]
                
                scene = self.scene_manager.scenes[pattern_state.scene_id]
                
                if pattern_state.effect_id >= len(scene.effects):
                    return [[0, 0, 0] for _ in range(led_count)]
                
                effect = scene.effects[pattern_state.effect_id]
                
                if pattern_state.palette_id >= len(scene.palettes):
                    palette = scene.palettes[0] if scene.palettes else [[255, 255, 255]] * 6
                else:
                    palette = scene.palettes[pattern_state.palette_id]
                
                led_array = [[0, 0, 0] for _ in range(led_count)]
                
                effect.render_to_led_array(palette, current_time, led_array)
                
                return led_array
                
        except Exception as e:
            logger.error(f"Error calculating pattern colors: {e}")
            return [[0, 0, 0] for _ in range(led_count)]


class DissolveTransition:
    """
    Manages dual pattern dissolve transition with simultaneous fade-out and fade-in
    Both patterns continue animating while crossfading according to per-LED timing
    """
    
    def __init__(self, led_count: int = 225):
        self.led_count = led_count
        self.phase = DissolvePhase.COMPLETED
        self.is_active = False
        
        self.old_pattern: Optional[PatternState] = None
        self.new_pattern: Optional[PatternState] = None
        
        self.pattern_data: List[List[int]] = []
        self.start_time: float = 0.0
        
        self.led_states: List[LEDCrossfadeState] = []
        self._initialize_led_states()
        
        self.calculator: Optional[DualPatternCalculator] = None
        
        self._lock = threading.RLock()
        
    def _initialize_led_states(self):
        """Initialize per-LED crossfade states"""
        self.led_states = [LEDCrossfadeState() for _ in range(self.led_count)]
        
    def set_calculator(self, calculator: DualPatternCalculator):
        """Set the dual pattern calculator"""
        self.calculator = calculator
        
    def start_dissolve(self, 
                      old_pattern: PatternState,
                      new_pattern: PatternState,
                      pattern_data: List[List[int]],
                      led_count: int):
        """
        Start dual pattern dissolve transition with simultaneous crossfade
        
        Args:
            old_pattern: Current pattern to fade out (while continuing animation)
            new_pattern: Target pattern to fade in (while continuing animation)
            pattern_data: Timing data [[delay_ms, duration_ms, start_led, end_led], ...]
            led_count: Number of LEDs
        """
        logger.info("Starting dual pattern dissolve:")
        logger.info(f"  Old pattern: Scene {old_pattern.scene_id}, Effect {old_pattern.effect_id}, Palette {old_pattern.palette_id}")
        logger.info(f"  New pattern: Scene {new_pattern.scene_id}, Effect {new_pattern.effect_id}, Palette {new_pattern.palette_id}")
        logger.info(f"  Pattern data: {len(pattern_data)} transitions")
        logger.info(f"  LED count: {led_count}")
        
        with self._lock:
            if self.led_count != led_count:
                self.led_count = led_count
                self._initialize_led_states()
            
            for led_state in self.led_states:
                led_state.crossfade_start_time = 0.0
                led_state.crossfade_duration_ms = 0
                led_state.blend_progress = 0.0
            
            self.old_pattern = old_pattern
            self.new_pattern = new_pattern
            self.pattern_data = pattern_data
            self.start_time = time.time()
            
            if not pattern_data:
                logger.warning("Empty pattern data - transition will be instant")
                self.phase = DissolvePhase.COMPLETED
                self.is_active = False
                return
            
            valid_transitions = self._setup_crossfade_timing(pattern_data)
            
            if not valid_transitions:
                logger.warning("No valid transitions - completing immediately")
                self.phase = DissolvePhase.COMPLETED
                self.is_active = False
                return
            
            self.phase = DissolvePhase.CROSSFADING
            self.is_active = True
            
            logger.info(f"Dual dissolve started: {len(valid_transitions)} valid transitions")
            
    def _setup_crossfade_timing(self, pattern_data: List[List[int]]) -> List[List[int]]:
        """
        Setup crossfade timing for each LED range according to pattern
        
        Args:
            pattern_data: Raw pattern timing data
            
        Returns:
            List of valid transitions
        """
        valid_transitions = []
        leds_with_timing = 0
        
        for i, transition in enumerate(pattern_data):
            if not self._validate_transition_format(transition):
                logger.warning(f"Invalid transition {i}: {transition}")
                continue
                
            delay_ms, duration_ms, start_led, end_led = transition
            
            start_led = max(0, min(start_led, self.led_count - 1))
            end_led = max(start_led, min(end_led, self.led_count - 1))
            
            if start_led > end_led or end_led >= self.led_count:
                logger.warning(f"Invalid LED range {start_led}-{end_led} for transition {i}")
                continue
            
            crossfade_start = self.start_time + (delay_ms / 1000.0)
            
            leds_in_transition = 0
            for led_idx in range(start_led, end_led + 1):
                if led_idx < len(self.led_states):
                    led_state = self.led_states[led_idx]
                    
                    led_state.crossfade_start_time = crossfade_start
                    led_state.crossfade_duration_ms = duration_ms
                    led_state.blend_progress = 0.0
                    
                    leds_in_transition += 1
                    leds_with_timing += 1
            
            valid_transitions.append([delay_ms, duration_ms, start_led, end_led])
            logger.info(f"Transition {i}: {delay_ms}ms delay, {duration_ms}ms duration, LEDs {start_led}-{end_led} ({leds_in_transition} LEDs)")
        
        logger.info(f"Crossfade timing setup: {leds_with_timing} LEDs have timing")
        return valid_transitions
        
    def _validate_transition_format(self, transition) -> bool:
        """
        Validate transition data format
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
        Update crossfade progress and return blended LED array from both patterns
        Both patterns continue animating while being crossfaded
        
        Args:
            current_time: Current timestamp for timing calculations
            
        Returns:
            Blended LED color array with dual pattern crossfade
        """
        if not self.is_active or self.phase != DissolvePhase.CROSSFADING:
            if self.new_pattern and self.calculator:
                return self.calculator.calculate_pattern_colors(
                    self.new_pattern, current_time, self.led_count
                )
            return [[0, 0, 0] for _ in range(self.led_count)]
        
        if not self.calculator or not self.old_pattern or not self.new_pattern:
            logger.error("Missing calculator or pattern states")
            self.phase = DissolvePhase.COMPLETED
            self.is_active = False
            return [[0, 0, 0] for _ in range(self.led_count)]
        
        old_colors = self.calculator.calculate_pattern_colors(
            self.old_pattern, current_time, self.led_count
        )
        new_colors = self.calculator.calculate_pattern_colors(
            self.new_pattern, current_time, self.led_count
        )
        
        result_array = [[0, 0, 0] for _ in range(self.led_count)]
        completed_count = 0
        total_with_timing = 0
        
        for led_idx in range(self.led_count):
            if led_idx >= len(self.led_states):
                result_array[led_idx] = new_colors[led_idx] if led_idx < len(new_colors) else [0, 0, 0]
                continue
                
            led_state = self.led_states[led_idx]
            
            if led_state.crossfade_duration_ms == 0:
                result_array[led_idx] = new_colors[led_idx] if led_idx < len(new_colors) else [0, 0, 0]
                continue
            
            total_with_timing += 1
            
            if current_time < led_state.crossfade_start_time:
                led_state.blend_progress = 0.0
                result_array[led_idx] = old_colors[led_idx] if led_idx < len(old_colors) else [0, 0, 0]
            else:
                elapsed_ms = (current_time - led_state.crossfade_start_time) * 1000
                
                if elapsed_ms >= led_state.crossfade_duration_ms:
                    led_state.blend_progress = 1.0
                    result_array[led_idx] = new_colors[led_idx] if led_idx < len(new_colors) else [0, 0, 0]
                    completed_count += 1
                else:
                    if led_state.crossfade_duration_ms > 0:
                        progress = elapsed_ms / led_state.crossfade_duration_ms
                        progress = min(1.0, max(0.0, progress))
                    else:
                        progress = 1.0
                    
                    led_state.blend_progress = progress
                    
                    old_color = old_colors[led_idx] if led_idx < len(old_colors) else [0, 0, 0]
                    new_color = new_colors[led_idx] if led_idx < len(new_colors) else [0, 0, 0]
                    
                    old_factor = 1.0 - progress
                    new_factor = progress
                    
                    result_array[led_idx] = [
                        int(old_color[0] * old_factor + new_color[0] * new_factor),
                        int(old_color[1] * old_factor + new_color[1] * new_factor),
                        int(old_color[2] * old_factor + new_color[2] * new_factor)
                    ]
        
        if total_with_timing > 0 and completed_count >= total_with_timing:
            self.phase = DissolvePhase.COMPLETED
            self.is_active = False
            logger.info(f"Dual dissolve completed: {completed_count}/{total_with_timing} LEDs finished")
        
        return result_array