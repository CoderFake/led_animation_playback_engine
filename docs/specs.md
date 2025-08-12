# LED Animation Playback Engine -  Specification (Updated 11/08/2025)

## Version History

| Version | Date | Changes | Status |
|---------|------|---------|---------|
| v1.1.2 | 2025-08-11 | **Transparency & Interpolation Bug Fixes**<br>• Fix transparency=1.0 bug - now fully transparent (returns black)<br>• Add color interpolation between segments for smooth gradients<br>• Add transparency interpolation between segments<br>• Update ColorUtils.apply_transparency() logic<br>• Update Segment.get_led_colors_with_timing() with interpolation<br>• Enhanced visual quality with smooth color transitions | Complete |
| v1.1.0 | 2025-08-07 | **OSC Pattern System & Animation Control**<br>• Remove auto-trigger from change_scene/effect/palette<br>• Add /change_pattern OSC for explicit pattern execution<br>• Add /pause and /resume OSC commands<br>• Implement cache-first pattern changes<br>• Initial scene animation starts immediately after JSON load<br>• Dissolve transitions only on /change_pattern trigger<br>• Enhanced animation state management | Complete |
| v1.0.1 | 2025-08-04 | **Position System Update & Brightness Fix**<br>• Convert position fields from float to int for precision<br>• Fix get_brightness_at_time calculation logic<br>• Add integer truncation with fractional accumulator<br>• Enhance test coverage for position handling<br>• Update color utilities for integer positioning<br>• Improve LED array indexing consistency | Complete |
| v1.0.0 | 2025-07-10 | **Core Architecture Overhaul**<br>• Unified zero-origin ID system<br>• Time-based dimmer implementation<br>• Flexible FPS configuration<br>• Extended speed range (0-1023%)<br>• Fractional movement with fade effects<br>• Multi-device output support<br>• Dissolve pattern system | Complete |

## Project Overview

### Main Objective
Build a **LED Animation Playback Engine** system that generates and sends **LED control signals (RGB arrays)** in real-time at **configurable FPS**, based on specified parameters like **Scene**, **Effect**, and **Palette**.

### Key Changes in This Version (v1.1.2)
- **Transparency Bug Fix**: `transparency=1.0` now correctly produces fully transparent (black) LEDs
- **Color Interpolation**: Added smooth color gradients between segments within the same segment definition
- **Transparency Interpolation**: Added smooth transparency transitions between segments
- **Enhanced Visual Quality**: Segments now display smooth color transitions instead of discrete color blocks
- **Updated ColorUtils**: Fixed apply_transparency() method logic for correct transparency handling
- **Updated Segment Logic**: Enhanced get_led_colors_with_timing() to support interpolation between adjacent color/transparency values

### Key Changes in Previous Version (v1.1.0)
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

## Bug Fixes (v1.1.2)

### Transparency Bug Fix
**Problem**: `transparency=1.0` was not producing fully transparent LEDs, causing background colors to show through incorrectly.

**Solution**: 
- Updated `ColorUtils.apply_transparency()` to explicitly return `[0, 0, 0]` when `transparency >= 1.0`
- Fixed logic: `transparency=0.0` = fully opaque, `transparency=1.0` = fully transparent (black)

```python
# Before (incorrect):
def apply_transparency(color, transparency):
    alpha_factor = 1.0 - transparency
    return [int(c * alpha_factor) for c in color]

# After (fixed):
def apply_transparency(color, transparency):
    transparency = max(0.0, min(1.0, transparency))
    if transparency >= 1.0:
        return [0, 0, 0]  # Fully transparent = black
    alpha_factor = 1.0 - transparency
    return [int(c * alpha_factor) for c in color]
```

### Interpolation Enhancement
**Problem**: No smooth transitions between color segments - each segment displayed uniform color based on its index.

**Solution**:
- Added `ColorUtils.interpolate_color()` and `ColorUtils.interpolate_transparency()` methods
- Updated `Segment.get_led_colors_with_timing()` to interpolate between adjacent segments
- Each LED within a segment now calculates its color based on its position progress toward the next segment

```python
# New interpolation methods in ColorUtils:
@staticmethod
def interpolate_color(color1: list, color2: list, factor: float) -> list:
    factor = max(0.0, min(1.0, factor))
    return [int(color1[i] + (color2[i] - color1[i]) * factor) for i in range(3)]

@staticmethod
def interpolate_transparency(transparency1: float, transparency2: float, factor: float) -> float:
    factor = max(0.0, min(1.0, factor))
    return transparency1 + (transparency2 - transparency1) * factor
```

### Test Cases
**Test Case 1**: Transparency verification
- Segment with `transparency=[0.0, 1.0]`, `length=[50, 50]`
- Expected: First 50 LEDs bright, next 50 LEDs black

**Test Case 2**: Interpolation verification  
- Segment with `color=[0, 0, 1]`, `transparency=[1.0, 0.0, 0.0]`, `length=[30, 30]`
- Expected: Smooth gradient from transparent red to opaque blue

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
│ (led_count,fps) │       │  (simplified)   │       │ (interpolation) │
└─────────────────┘       └─────────────────┘       └─────────────────┘
```

## Core Components
- **Animation Engine**: Main processor with configurable FPS loop
- **Scene Manager**: Manages Scene, Effect, Palette and transitions
- **Dissolve Manager**: Handles dissolve transition patterns
- **OSC Handler**: Processes input OSC messages
- **Multi-Device LED Output**: Distributes RGB data to multiple devices
- **Performance Monitor**: System performance tracking
- **ColorUtils**: Enhanced with interpolation and fixed transparency handling

## Core Functions

### LED Animation Playback Engine
- Generate RGB arrays for LEDs at **configurable FPS** based on **Scene × Effect × Palette** combinations
- Support **playbook speed** control (0-1023%) and **dissolve transition** patterns
- Real-time animation processing with consistent frame timing
- **Multi-device output** with full copy or range-based distribution
- **Smooth color interpolation** within segments for enhanced visual quality

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

### Segment Model (Updated v1.1.2)

```python
@dataclass
class Segment:
    segment_id: int
    color: List[int]                        
    transparency: List[float]              
    length: List[int]                     
    move_speed: float
    move_range: List[int]
    initial_position: int                   
    current_position: int                   
    is_edge_reflect: bool
    dimmer_time: List[List[int]]           
    segment_start_time: float = 0.0      
    
    def __post_init__(self):
        """Initialize segment timing when created"""
        self.segment_start_time = time.time()
        self._fractional_accumulator = 0.0
    
    def get_brightness_at_time(self, current_time: float) -> float:
        """Get brightness based on elapsed time since segment start"""
        # ... (same as v1.0.1)
    
    def get_led_colors_with_timing(self, palette: List[List[int]], current_time: float) -> List[List[int]]:
        """Get LED colors with interpolation support - UPDATED v1.1.2"""
        try:
            brightness_factor = self.get_brightness_at_time(current_time)
            
            if brightness_factor <= 0.0:
                return []
            
            colors = []
            
            # Process segments with interpolation between adjacent segments
            for part_index in range(len(self.length)):
                part_length = self.length[part_index]
                if part_length <= 0:
                    continue
                
                color_index = self.color[part_index] if part_index < len(self.color) else 0
                transparency = self.transparency[part_index] if part_index < len(self.transparency) else 0.0
                
                # Check if we should interpolate to next segment
                next_color_index = None
                next_transparency = None
                
                if part_index + 1 < len(self.color):
                    next_color_index = self.color[part_index + 1]
                    next_transparency = self.transparency[part_index + 1] if part_index + 1 < len(self.transparency) else 0.0
                
                # Generate LEDs for this segment with interpolation
                for led_in_part in range(part_length):
                    if next_color_index is not None and next_transparency is not None and part_length > 1:
                        # Calculate interpolation factor
                        progress = led_in_part / (part_length - 1)
                        
                        # Interpolate color
                        base_color1 = ColorUtils.get_palette_color(palette, color_index)
                        base_color2 = ColorUtils.get_palette_color(palette, next_color_index)
                        interpolated_color = ColorUtils.interpolate_color(base_color1, base_color2, progress)
                        
                        # Interpolate transparency
                        interpolated_transparency = ColorUtils.interpolate_transparency(transparency, next_transparency, progress)
                        
                        final_color = ColorUtils.calculate_segment_color(
                            interpolated_color, interpolated_transparency, brightness_factor
                        )
                    else:
                        # No interpolation - use solid color
                        base_color = ColorUtils.get_palette_color(palette, color_index)
                        final_color = ColorUtils.calculate_segment_color(
                            base_color, transparency, brightness_factor
                        )
                    
                    colors.append(final_color)
            
            # Handle extra colors beyond length array (no interpolation)
            if len(self.color) > len(self.length):
                for extra_index in range(len(self.length), len(self.color)):
                    color_index = self.color[extra_index]
                    transparency = self.transparency[extra_index] if extra_index < len(self.transparency) else 0.0
                    
                    base_color = ColorUtils.get_palette_color(palette, color_index)
                    final_color = ColorUtils.calculate_segment_color(
                        base_color, transparency, brightness_factor
                    )
                    colors.append(final_color)
            
            return colors
            
        except Exception as e:
            return []
```

### ColorUtils Updates (v1.1.2)

```python
class ColorUtils:
    @staticmethod
    def apply_transparency(color, transparency: float) -> list:
        """Apply transparency to color - FIXED v1.1.2"""
        transparency = max(0.0, min(1.0, transparency))
        
        # Fix: When transparency=1.0, should be fully transparent (black)
        if transparency >= 1.0:
            return [0, 0, 0]
        
        alpha_factor = 1.0 - transparency
        return [int(c * alpha_factor) for c in color]
    
    @staticmethod
    def interpolate_color(color1: list, color2: list, factor: float) -> list:
        """Interpolate between two colors - NEW v1.1.2"""
        factor = max(0.0, min(1.0, factor))
        return [
            int(color1[i] + (color2[i] - color1[i]) * factor)
            for i in range(3)
        ]
    
    @staticmethod
    def interpolate_transparency(transparency1: float, transparency2: float, factor: float) -> float:
        """Interpolate between two transparency values - NEW v1.1.2"""
        factor = max(0.0, min(1.0, factor))
        return transparency1 + (transparency2 - transparency1) * factor
```

## Breaking Changes Summary

### Bug Fixes (v1.1.2)
1. **Transparency Behavior**: `transparency=1.0` now correctly produces black (fully transparent) LEDs
2. **Visual Enhancement**: Segments now display smooth color gradients instead of uniform color blocks
3. **ColorUtils Updates**: Fixed transparency logic and added interpolation methods
4. **Backward Compatibility**: Existing JSON files continue to work, but will display enhanced visual quality

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

### Algorithm Changes (v1.1.2)
1. **Transparency Handling**: Fixed logic for correct transparency behavior
2. **Color Interpolation**: Added smooth color transitions within segments
3. **Visual Quality**: Enhanced rendering with gradient effects

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
- **Bug Fixes**: No migration required - fixes improve visual quality without breaking compatibility
- **Interpolation**: Existing segments will automatically display enhanced gradient effects
- **Transparency**: transparency=1.0 segments will now correctly appear transparent (black)
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
- **Interpolation**: Smooth color gradients with minimal performance impact
- **Test Coverage**: Comprehensive testing for all position handling scenarios and bug fixes

---