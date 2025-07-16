# LED Animation Playback Engine - Complete Specification (Updated 10/07/2025)

## Project Overview

### Main Objective
Build a **LED Animation Playback Engine** system that generates and sends **LED control signals (RGB arrays)** in real-time at **configurable FPS**, based on specified parameters like **Scene**, **Effect**, and **Palette**.

### Key Changes in This Version
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
│ (led_count,fps) │       │  (simplified)   │       │ (flexible size) │
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
- Support **playback speed** control (0-1023%) and **dissolve transition** patterns
- Real-time animation processing with consistent frame timing
- **Multi-device output** with full copy or range-based distribution

### OSC Message Input Processing
```
/load_json string                           # Auto-append .json if no extension
/change_scene int                           # Zero-origin scene ID
/change_effect int                          # Zero-origin effect ID  
/change_palette int                         # Zero-origin
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

### Segment Model 

```python
@dataclass
class Segment:
    segment_id: int
    color: List[int]                        
    transparency: List[float]              
    length: List[int]                     
    move_speed: float
    move_range: List[int]
    current_position: float
    is_edge_reflect: bool
    dimmer_time: List[List[int]]           
    segment_start_time: float = 0.0      
    
    def __post_init__(self):
        """Initialize segment timing when created"""
        self.segment_start_time = time.time()
    
    def get_brightness_at_time(self, current_time: float) -> float:
        """Get brightness based on elapsed time since segment start"""
        elapsed_ms = (current_time - self.segment_start_time) * 1000
        
        if not self.dimmer_time:
            return 1.0
        
        # Calculate total cycle time
        total_cycle_ms = sum(transition[0] for transition in self.dimmer_time)
        if total_cycle_ms <= 0:
            return 1.0
        
        # Handle looping - reset to beginning when cycle completes
        elapsed_ms = elapsed_ms % total_cycle_ms
        
        # Find current transition phase
        current_time_ms = 0
        for duration_ms, start_brightness, end_brightness in self.dimmer_time:
            if elapsed_ms <= current_time_ms + duration_ms:
                # Calculate progress within this transition (0.0 to 1.0)
                progress = (elapsed_ms - current_time_ms) / duration_ms
                # Linear interpolation between start and end brightness
                brightness = start_brightness + (end_brightness - start_brightness) * progress
                return max(0.0, min(1.0, brightness / 100.0))
            current_time_ms += duration_ms
        
        return 1.0  # Fallback
    
    def reset_animation_timing(self):
        """Reset timing when segment direction changes or position resets"""
        self.segment_start_time = time.time()
    
    def update_position(self, delta_time: float):
        """Update position and handle boundary conditions"""
        if abs(self.move_speed) < 0.001:
            return
            
        self.current_position += self.move_speed * delta_time
        
        # Handle boundary conditions
        if self.is_edge_reflect and len(self.move_range) >= 2:
            min_pos, max_pos = self.move_range[0], self.move_range[1]
            
            if self.current_position <= min_pos:
                self.current_position = min_pos
                self.move_speed = abs(self.move_speed)
                self.reset_animation_timing()  # Reset timing on direction change
            elif self.current_position >= max_pos:
                self.current_position = max_pos
                self.move_speed = -abs(self.move_speed)
                self.reset_animation_timing()  # Reset timing on direction change
        elif not self.is_edge_reflect and len(self.move_range) >= 2:
            # Wrap around mode
            min_pos, max_pos = self.move_range[0], self.move_range[1]
            range_size = max_pos - min_pos
            if range_size > 0:
                relative_pos = (self.current_position - min_pos) % range_size
                self.current_position = min_pos + relative_pos
    
    def get_led_colors_with_timing(self, palette: List[List[int]], current_time: float) -> List[List[int]]:
        """Get LED colors with time-based brightness and fractional positioning"""
        if not self.color or not palette:
            return []
        
        brightness_factor = self.get_brightness_at_time(current_time)
        
        colors = []
        current_led_index = 0
        
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
                current_led_index += 1
        
        return colors
    
    def render_to_led_array(self, palette: List[List[int]], current_time: float, 
                           led_array: List[List[int]]) -> None:
        """Render segment to LED array with fractional positioning"""
        segment_colors = self.get_led_colors_with_timing(palette, current_time)
        
        if not segment_colors:
            return
        
        base_position = int(self.current_position)
        fractional_part = self.current_position - base_position
        
        for i, color in enumerate(segment_colors):
            led_index = base_position + i
            
            if 0 <= led_index < len(led_array):
                if len(segment_colors) > 1:
                    if i == 0:
                        fade_factor = fractional_part
                        faded_color = [int(c * fade_factor) for c in color]
                    elif i == len(segment_colors) - 1:
                        fade_factor = 1.0 - fractional_part
                        faded_color = [int(c * fade_factor) for c in color]
                    else:
                        faded_color = color
                else:
                    faded_color = color
                
                for j in range(3):
                    led_array[led_index][j] = min(255, led_array[led_index][j] + faded_color[j])
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
    """Get LED output with time-based brightness and fractional positioning"""
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
        
        # Render each segment with timing
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
              "initial_position": 0,
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

### Dissolve Transition Flow
```
Receive Switch Command ──▶ Load Dissolve Pattern ──▶ Start Simultaneous Fade  
          │                         ▲                         │
          ▼                         │                         ▼
    Save before/after  ───▶  Calculate transition    Apply blend per LED
    states                   timing per LED range   based on pattern timing
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
```

## Breaking Changes Summary

### Data Structure Changes
1. **dimmer_time** format: 1D array → 2D array with timing
2. **ID System**: All IDs changed from 1-origin to 0-origin
3. **Palette Parameter**: `/change_palette` changed from string to int
4. **Data Structure**: Palettes and effects changed from dict to array
5. **Removed Parameters**: gradient, gradient_colors, fade, dimmer_time_ratio
6. **Scene Configuration**: led_count, fps moved from Effect to Scene

### Algorithm Changes
1. **Brightness Calculation**: Position-based → Time-based
2. **Movement Rendering**: Integer positions → Fractional with fade effects
3. **Speed Range**: Extended from 0-200% to 0-1023%
4. **Transition System**: Simple fade → Pattern-based dissolve

### Migration Requirements
- **All existing JSON files** need format conversion
- **Timing behavior** will change significantly
- **Visual output** will be different due to time-based brightness
- **Performance characteristics** may change due to fractional rendering

## Performance Requirements

- **Frame Rate**: Configurable FPS (stable performance up to 60 FPS)
- **Speed Range**: 0-1023% (expanded from 0-200%)
- **Multi-Device**: Support multiple output destinations
- **Dissolve**: Smooth transitions with configurable patterns
- **Fractional Movement**: Sub-pixel accuracy with fade effects

---
