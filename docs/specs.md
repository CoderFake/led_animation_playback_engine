# LED Animation Playback Engine -  Specification (Updated 07/08/2025)

## Version History

| Version | Date | Changes | Status |
|---------|------|---------|---------|
| v1.1.0 | 2025-08-07 | **OSC Pattern System & Animation Control**<br>• Remove auto-trigger from change_scene/effect/palette<br>• Add /change_pattern OSC for explicit pattern execution<br>• Add /pause and /resume OSC commands<br>• Implement cache-first pattern changes<br>• Initial scene animation starts immediately after JSON load<br>• Dissolve transitions only on /change_pattern trigger<br>• Enhanced animation state management | Complete |
| v1.0.1 | 2025-08-04 | **Position System Update & Brightness Fix**<br>• Convert position fields from float to int for precision<br>• Fix get_brightness_at_time calculation logic<br>• Add integer truncation with fractional accumulator<br>• Enhance test coverage for position handling<br>• Update color utilities for integer positioning<br>• Improve LED array indexing consistency | Complete |
| v1.0.0 | 2025-07-10 | **Core Architecture Overhaul**<br>• Unified zero-origin ID system<br>• Time-based dimmer implementation<br>• Flexible FPS configuration<br>• Extended speed range (0-1023%)<br>• Fractional movement with fade effects<br>• Multi-device output support<br>• Dissolve pattern system | Complete |

## Project Overview

### Main Objective
Build a **LED Animation Playback Engine** system that generates and sends **LED control signals (RGB arrays)** in real-time at **configurable FPS**, based on specified parameters like **Scene**, **Effect**, and **Palette**.

### Key Changes in This Version (v1.1.0)
- **Cache-first pattern changes**: Scene/effect/palette changes are cached only, no immediate visual changes
- **Explicit pattern execution**: New `/change_pattern` OSC command triggers actual dissolve transitions
- **Animation control**: Added `/pause` and `/resume` OSC commands for playback control
- **Initial animation start**: Scene animation begins immediately after JSON load (no cache needed)
- **Enhanced state management**: Clear separation between cached changes and active animation
- **Dissolve on demand**: Transitions only occur when explicitly triggered via `/change_pattern`

### Key Changes in Previous Version (v1.0.1)
- **Integer position system** for improved precision and consistency
- **Enhanced brightness calculation** with proper boundary handling
- **Fractional accumulator** for smooth position updates
- **Comprehensive test coverage** for position handling and edge cases
- **Improved LED array indexing** throughout the codebase

### Key Changes in Previous Version (v1.0.0)
- **Unified zero-origin ID system** for scene, effect, palette
- **Fixed dimmer_time implementation** - changed from position-based to time-based
- **Flexible FPS** instead of fixed 60FPS
- **Extended speed range** from 0-1023% (previously 0-200%)
- **Fractional movement** with fade-in/fade-out effects
- **Multi-device output** with full copy or range-based distribution
- **Dissolve pattern system** replaces simple fade transitions
- **Removed** gradient, gradient_colors, fade, dimmer_time_ratio parameters

## Architecture Overview

### System Architecture
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   OSC Input     │───▶│  Animation      │───▶│   OSC Output    │
│   Handler       │    │   Engine        │    │   Handler       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
      │                        ▲    │                  │
      │                        |    │                  │
      │      ┌─────────────────┘    │                  │   
      ▼      |                      ▼                  ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Scene Manager   │    │  Performance    │    │ Multi-Device    │
│ + Dissolve Mgr  │    │     Monitor     │    │ LED Output Mgr  │───▶ Remote Devices
└─────────────────┘    └─────────────────┘    └─────────────────┘
        ▲                                             
        │
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│  Scene Class    │ ◀───  │   Effect Class  │  ◀─── │  Segment Class  │
│ (led_count,fps) │       │  (simplified)   │       │ (integer pos)   │
└─────────────────┘       └─────────────────┘       └─────────────────┘
```

## Core Components
- **Animation Engine**: Main processor with configurable FPS loop
- **Scene Manager**: Manages Scene, Effect, Palette and transitions
- **Dissolve Manager**: Handles dissolve transition patterns
- **OSC Handler**: Processes input OSC messages
- **Multi-Device LED Output**: Distributes RGB data to multiple devices
- **Performance Monitor**: System performance tracking

## Core Functions

### LED Animation Playback Engine
- Generate RGB arrays for LEDs at **configurable FPS** based on **Scene × Effect × Palette** combinations
- Support **playbook speed** control (0-1023%) and **dissolve transition** patterns
- Real-time animation processing with consistent frame timing
- **Multi-device output** with full copy or range-based distribution

### OSC Message Input Processing
```
/load_json string                           # Auto-append .json if no extension
/change_scene int                           # Cache scene change (zero-origin scene ID)
/change_effect int                          # Cache effect change (zero-origin effect ID)  
/change_palette int                         # Cache palette change (zero-origin)
/change_pattern                             # Execute cached changes with dissolve
/pause                                      # Pause animation playback
/resume                                     # Resume animation playback
/palette/{palette_id}/{color_id(0~5)} int[3] (r, g, b)
/load_dissolve_json string                  # Load dissolve patterns
/set_dissolve_pattern int                   # Set dissolve pattern (0-origin)
/set_speed_percent int                      # Expanded range: 0-1023%
/master_brightness int                      # Master brightness: 0-255
```

### OSC Message Output Processing
- Send generated RGB arrays to `/light/serial` address each frame
- **Multi-device support** with two modes:
  - **Full copy mode**: Send complete RGB data to all devices
  - **Range mode**: Send specific LED ranges to different devices

## Data Structures

### Scene Model
```python
@dataclass
class Scene:
    scene_id: int
    led_count: int = 225                  
    fps: int = 60                          
    current_effect_id: int = 0              
    current_palette_id: int = 0             
    palettes: List[List[List[int]]]         
    effects: List[Effect]                  
```

### Effect Model (Simplified)
```python
@dataclass
class Effect:
    effect_id: int
    segments: List[Segment]                 
```

### Segment Model (Updated v1.0.1)

```python
@dataclass
class Segment:
    segment_id: int
    color: List[int]                        
    transparency: List[float]              
    length: List[int]                     
    move_speed: float
    move_range: List[int]
    initial_position: int                   # Updated: int instead of float
    current_position: int                   # Updated: int instead of float
    is_edge_reflect: bool
    dimmer_time: List[List[int]]           
    segment_start_time: float = 0.0      
    
    def __post_init__(self):
        """Initialize segment timing when created"""
        self.segment_start_time = time.time()
        self._fractional_accumulator = 0.0  # New: for smooth movement
    
    def get_brightness_at_time(self, current_time: float) -> float:
        """Get brightness based on elapsed time since segment start - UPDATED v1.0.1"""
        try:
            if not self.dimmer_time:
                return 1.0
                
            elapsed_ms = (current_time - self.segment_start_time) * 1000
            
            total_cycle_ms = sum(max(1, transition[0]) for transition in self.dimmer_time)
            if total_cycle_ms <= 0:
                return 1.0
            
            # Handle cycling - modulo for repeating pattern
            cycle_elapsed_ms = elapsed_ms % total_cycle_ms
            
            # Handle boundary case: if exactly at cycle end, treat as end of last transition
            if cycle_elapsed_ms == 0 and elapsed_ms > 0:
                cycle_elapsed_ms = total_cycle_ms
            
            current_time_ms = 0
            for duration_ms, start_brightness, end_brightness in self.dimmer_time:
                duration_ms = max(1, int(duration_ms))
                
                # Check if elapsed time falls within this transition
                if cycle_elapsed_ms <= current_time_ms + duration_ms:
                    # Calculate progress within this transition (0.0 to 1.0)
                    progress = (cycle_elapsed_ms - current_time_ms) / duration_ms
                    progress = max(0.0, min(1.0, progress))
                    
                    # Linear interpolation between start and end brightness
                    brightness = start_brightness + (end_brightness - start_brightness) * progress
                    result = brightness / 100.0
                    return max(0.0, min(1.0, result))
                    
                current_time_ms += duration_ms
            
            # Fallback: return the last brightness value
            if self.dimmer_time:
                last_brightness = self.dimmer_time[-1][2] 
                return max(0.0, min(1.0, last_brightness / 100.0))
            
            return 1.0
            
        except Exception as e:
            return 1.0
    
    def reset_animation_timing(self):
        """Reset timing when segment direction changes or position resets"""
        self.segment_start_time = time.time()
    
    def update_position(self, delta_time: float):
        """Update position with integer truncation and fractional accumulator - UPDATED v1.0.1"""
        if abs(self.move_speed) < 0.001:
            return
        
        if not hasattr(self, '_fractional_accumulator'):
            self._fractional_accumulator = 0.0
        
        # Accumulate fractional movement
        self._fractional_accumulator += self.move_speed * delta_time
        
        # Apply integer changes when accumulator exceeds 1.0
        if abs(self._fractional_accumulator) >= 1.0:
            position_change = int(self._fractional_accumulator)
            self.current_position += position_change
            self._fractional_accumulator -= position_change
        
        # Handle boundary conditions with integer positions
        if self.is_edge_reflect and len(self.move_range) >= 2:
            min_pos, max_pos = self.move_range[0], self.move_range[1]
            
            if self.current_position <= min_pos:
                self.current_position = min_pos
                self.move_speed = abs(self.move_speed)
                self.reset_animation_timing()  # Reset timing on direction change
                self._fractional_accumulator = 0.0
            elif self.current_position >= max_pos:
                self.current_position = max_pos
                self.move_speed = -abs(self.move_speed)
                self.reset_animation_timing()  # Reset timing on direction change
                self._fractional_accumulator = 0.0
        elif not self.is_edge_reflect and len(self.move_range) >= 2:
            # Wrap around mode with integer arithmetic
            min_pos, max_pos = self.move_range[0], self.move_range[1]
            range_size = max_pos - min_pos
            if range_size > 0:
                if self.current_position < min_pos:
                    offset = min_pos - self.current_position
                    self.current_position = max_pos - (offset % range_size)
                elif self.current_position > max_pos:
                    offset = self.current_position - max_pos
                    self.current_position = min_pos + (offset % range_size)
    
    def get_led_colors_with_timing(self, palette: List[List[int]], current_time: float) -> List[List[int]]:
        """Get LED colors with time-based brightness and integer positioning - UPDATED v1.0.1"""
        if not self.color or not palette:
            return []
        
        brightness_factor = self.get_brightness_at_time(current_time)
        
        if brightness_factor <= 0.0:
            return []
        
        colors = []
        
        for part_index in range(len(self.length)):
            part_length = max(0, self.length[part_index])
            
            if part_length == 0:
                continue
            
            color_index = self.color[part_index] if part_index < len(self.color) else 0
            transparency = self.transparency[part_index] if part_index < len(self.transparency) else 0.0
            
            for led_in_part in range(part_length):
                if 0 <= color_index < len(palette):
                    base_color = palette[color_index][:3]
                else:
                    base_color = [0, 0, 0]
                
                # Apply transparency: 0.0 = opaque, 1.0 = transparent
                opacity = 1.0 - transparency
                color = [c * opacity for c in base_color]
                color = [c * brightness_factor for c in color]
                
                final_color = [max(0, min(255, int(c))) for c in color]
                colors.append(final_color)
        
        return colors
    
    def render_to_led_array(self, palette: List[List[int]], current_time: float, 
                           led_array: List[List[int]]) -> None:
        """Render segment to LED array with integer positioning - UPDATED v1.0.1"""
        segment_colors = self.get_led_colors_with_timing(palette, current_time)
        
        if not segment_colors:
            return
        
        # Use integer position directly
        base_position = int(self.current_position)
        
        for i, color in enumerate(segment_colors):
            led_index = base_position + i
            
            if 0 <= led_index < len(led_array):
                # Add colors to LED array with proper bounds checking
                for j in range(3):
                    if j < len(color):
                        led_array[led_index][j] = min(255, led_array[led_index][j] + color[j])
```

## Animation Engine Updates

### Animation Frame Processing
```python
def _update_frame(self, delta_time: float):
    current_time = time.time()
    
    # Apply speed multiplier
    adjusted_delta = delta_time * (self.speed_percent / 100.0)
    
    # Update scene manager animation
    self.scene_manager.update_animation(adjusted_delta)
    
    # Get LED output with time-based rendering
    led_colors = self.scene_manager.get_led_output_with_timing(current_time)
    
    # Apply master brightness
    if self.master_brightness < 255:
        brightness_factor = self.master_brightness / 255.0
        led_colors = [
            [int(c * brightness_factor) for c in color]
            for color in led_colors
        ]
    
    # Send to LED output
    self.led_output.send_led_data(led_colors)

# In scene_manager.py 
def get_led_output_with_timing(self, current_time: float) -> List[List[int]]:
    """Get LED output with time-based brightness and integer positioning"""
    with self._lock:
        if not self.active_scene_id or self.active_scene_id not in self.scenes:
            return [[0, 0, 0] for _ in range(EngineSettings.ANIMATION.led_count)]
        
        scene = self.scenes[self.active_scene_id]
        current_effect = scene.get_current_effect()
        
        if not current_effect:
            return [[0, 0, 0] for _ in range(EngineSettings.ANIMATION.led_count)]
        
        # Initialize LED array
        led_array = [[0, 0, 0] for _ in range(EngineSettings.ANIMATION.led_count)]
        palette = scene.get_current_palette()
        
        # Render each segment with timing and integer positions
        for segment in current_effect.segments.values():
            segment.render_to_led_array(palette, current_time, led_array)
        
        return led_array
```

## JSON File Structure

```json
{
  "scenes": [
    {
      "scene_id": 0,                   
      "led_count": 225,                
      "fps": 60,                      
      "current_effect_id": 0,          
      "current_palette_id": 0,         
      "palettes": [                     
        [[r,g,b], [r,g,b], [r,g,b], [r,g,b], [r,g,b], [r,g,b]],  
        [[r,g,b], [r,g,b], [r,g,b], [r,g,b], [r,g,b], [r,g,b]]   
      ],
      "effects": [                     
        {
          "effect_id": 0,               
          "segments": [                
            {
              "segment_id": 0,          
              "color": [0, 1, 2, 3, 4, 5],       
              "transparency": [1.0, 0.8, 0.6, 0.4, 0.2, 0.1],  
              "length": [30, 30, 30, 30, 30],     
              "move_speed": 25.0,
              "move_range": [0, 195],
              "initial_position": 0,        // Updated: int instead of float
              "current_position": 0,        // Updated: int instead of float
              "is_edge_reflect": true,
              "dimmer_time": [             
                [1000, 0, 100],         
                [1000, 100, 0]           
              ]
              // Removed: gradient, gradient_colors, fade, dimmer_time_ratio
            }
          ]
        }
      ]
    }
  ]
}
```

### Pattern Change System (v1.1.0)
```
Cache Phase:
/change_scene 1     ──▶ Cache scene=1, continue showing current animation
/change_effect 2    ──▶ Cache effect=2, continue showing current animation  
/change_palette 3   ──▶ Cache palette=3, continue showing current animation

Execution Phase:
/change_pattern     ──▶ Execute dissolve transition: OLD pattern → NEW pattern
```

### Animation State Flow (v1.1.0)
```
Initial Load:
/load_json ──▶ Load scenes ──▶ Start animation immediately (Scene 0, Effect 0, Palette 0)

Cache Changes:
/change_* ──▶ Cache new values ──▶ Continue current animation (no visual change)

Execute Changes:
/change_pattern ──▶ Dissolve transition ──▶ Switch to new pattern ──▶ Continue animation

Animation Control:
/pause ──▶ Stop animation loop ──▶ Black screen
/resume ──▶ Restart animation loop ──▶ Continue from current state
```

### Dissolve Transition Flow
```
Receive /change_pattern ──▶ Load Dissolve Pattern ──▶ Start Simultaneous Fade  
          │                         ▲                         │
          ▼                         │                         ▼
    Use cached values  ───▶  Calculate transition    Apply blend per LED
    as OLD/NEW states        timing per LED range   based on pattern timing
```

### Dissolve Pattern JSON Structure
```json
{
  "dissolve_patterns": {
    "0":[                                   // Pattern 0
      [0, 100, 0, 49],                 // [delay_ms, duration_ms, start_led, end_led]
      [250, 100, 50, 99],
      [500, 100, 100, 149],
      [750, 100, 150, 199]
    ],
    "1":[                                   // Pattern 1
      [0, 200, 0, 99],
      [300, 150, 100, 199]
    ]
  }
}
```

## Configuration Settings

#### Multi-Device Output Flow
```
Generate RGB Data ──▶ Apply Master Brightness ──▶ Distribute to Devices
       │                        │                        │
       ▼                        ▼                        ▼
   225 LEDs                Complete data          Device 1: Full copy
                                │                  Device 2: LEDs 0-112
                                └─────────────────▶ Device 3: LEDs 113-224
```

### Multi-Device Configuration
```python
class LEDDestination(BaseModel):
    ip: str
    port: int
    start_led: int = 0      # For range mode
    end_led: int = -1       # -1 means full range
    copy_mode: bool = True  # True=full copy, False=range

class EngineSettings:
    OSC = OSCConfig(
        input_host="127.0.0.1",
        input_port=8000,
        output_address="/light/serial"
    )
    
    ANIMATION = AnimationConfig(
        default_fps=60,                 # Configurable, not fixed
        default_led_count=225,
        master_brightness=255,
        led_destinations=[              # Multi-device support
            LEDDestination(ip="192.168.11.105", port=7000, copy_mode=True),
            LEDDestination(ip="192.168.11.106", port=7001, start_led=0, end_led=112, copy_mode=False),
            LEDDestination(ip="192.168.11.107", port=7002, start_led=113, end_led=224, copy_mode=False)
        ]
    )
    
    DISSOLVE = DissolveConfig(
        enabled=True,
        default_pattern_id=0
    )
```

## JSON Conversion Utility

### Convert dimmer_time Format
```python
def convert_dimmer_time(old_format: List[int]) -> List[List[int]]:
    """Convert 1D position-based dimmer_time to 2D time-based format"""
    if not old_format or len(old_format) < 2:
        return [[1000, 0, 100]]  # Default 1-second fade in
    
    new_format = []
    default_duration = 1000  # 1 second per transition
    
    for i in range(len(old_format) - 1):
        start_brightness = old_format[i]
        end_brightness = old_format[i + 1]
        new_format.append([default_duration, start_brightness, end_brightness])
    
    return new_format

def convert_positions_to_int(segment_data: dict) -> dict:
    """Convert position fields to integers - NEW in v1.0.1"""
    if 'initial_position' in segment_data:
        segment_data['initial_position'] = int(segment_data['initial_position'])
    if 'current_position' in segment_data:
        segment_data['current_position'] = int(segment_data['current_position'])
    return segment_data
```

## Breaking Changes Summary

### OSC Behavior Changes (v1.1.0)
1. **Scene/Effect/Palette Changes**: No longer trigger immediate visual changes - only cache values
2. **Pattern Execution**: New `/change_pattern` OSC required to execute cached changes with dissolve
3. **Animation Control**: Added `/pause` and `/resume` OSC commands for playback control
4. **Initial Animation**: Scene animation starts immediately after JSON load (no cache needed)
5. **Dissolve Triggers**: Dissolve transitions only occur on explicit `/change_pattern` calls

### Data Structure Changes (v1.0.1)
1. **Position Fields**: `initial_position` and `current_position` changed from float to int
2. **Brightness Calculation**: Enhanced logic with proper boundary handling
3. **Position Updates**: Added fractional accumulator for smooth movement
4. **LED Array Indexing**: All indexing operations use integers consistently

### Data Structure Changes (v1.0.0)
1. **dimmer_time** format: 1D array → 2D array with timing
2. **ID System**: All IDs changed from 1-origin to 0-origin
3. **Palette Parameter**: `/change_palette` changed from string to int
4. **Data Structure**: Palettes and effects changed from dict to array
5. **Removed Parameters**: gradient, gradient_colors, fade, dimmer_time_ratio
6. **Scene Configuration**: led_count, fps moved from Effect to Scene

### Algorithm Changes (v1.0.1)
1. **Position Handling**: Float positions → Integer positions with fractional accumulator
2. **Brightness Calculation**: Improved boundary case handling and cycle management
3. **LED Rendering**: Consistent integer indexing throughout pipeline

### Algorithm Changes (v1.0.0)
1. **Brightness Calculation**: Position-based → Time-based
2. **Movement Rendering**: Integer positions → Fractional with fade effects
3. **Speed Range**: Extended from 0-200% to 0-1023%
4. **Transition System**: Simple fade → Pattern-based dissolve

### Migration Requirements
- **OSC Integration**: Update client code to use `/change_pattern` for executing pattern changes
- **Animation Control**: Integrate `/pause` and `/resume` commands for playback control
- **Initial Load Behavior**: Scene animation now starts immediately after JSON load
- **Cache Awareness**: Understand that scene/effect/palette changes are cached until `/change_pattern`
- **Position Values**: Existing float positions will be converted to integers
- **Test Coverage**: Enhanced testing required for integer position behavior and new OSC behavior
- **Performance**: Improved numerical stability and reduced floating-point errors
- **Compatibility**: Maintains compatibility with existing JSON files through conversion

## Performance Requirements

- **Frame Rate**: Configurable FPS (stable performance up to 60 FPS)
- **Speed Range**: 0-1023% (expanded from 0-200%)
- **Multi-Device**: Support multiple output destinations
- **Dissolve**: Smooth transitions with configurable patterns
- **Integer Positioning**: Improved precision and reduced computational overhead
- **Test Coverage**: Comprehensive testing for all position handling scenarios

---
