# LED Animation Playback Engine - API Test Cases Documentation

## Test Categories

### 1. Scene Management Tests

#### 1.1 Load JSON Scene Test
**Endpoint**: `POST /api/v1/load_json`

**Test Case**: Load a scene from a JSON file
```python
Request Body:
{
    "file_path": "/path/to/scene.json"
}

```

#### 1.2 Change Scene Test
**Endpoint**: `POST /api/v1/change_scene`

**Test Case**: Change scene by ID
```python
Request Body:
{
    "scene_id": 1
}

```

### 2. Palette Management Tests

#### 2.1 Change Palette Test
**Endpoint**: `POST /api/v1/change_palette`

**Test Case**: Change palette by ID
```python
Request Body:
{
    "palette_id": 2
}
```

#### 2.2 Update Palette Color Test
**Endpoint**: `PUT /api/v1/palette/{palette_id}/{color_id}`

**Test Case**: Update a color in the palette
```python
URL: /api/v1/palette/1/3
Request Body:
{
    "r": 255,
    "g": 128,
    "b": 64
}
```

### 3. LED Control Tests

#### 3.1 Change Effect Test
**Endpoint**: `POST /api/v1/change_effect`

**Test Case**: Change effect by ID
```python
Request Body:
{
    "effect_id": 5
}
```

#### 3.2 Set Speed Percent Test
**Endpoint**: `POST /api/v1/set_speed_percent`

**Test Case**: Set animation speed (0-1023%)
```python
Request Body:
{
    "percent": 150
}
```

#### 3.3 Master Brightness Test
**Endpoint**: `POST /api/v1/master_brightness`

**Test Case**: Set master brightness (0-255)
```python
Request Body:
{
    "brightness": 200
}
```

#### 3.4 Dissolve Pattern Tests

##### 3.4.1 Load Dissolve JSON Test
**Endpoint**: `POST /api/v1/load_dissolve_json`

**Test Case**: Load dissolve pattern from JSON
```python
Request Body:
{
    "file_path": "/path/to/dissolve_pattern.json"
}
```

##### 3.4.2 Set Dissolve Pattern Test
**Endpoint**: `POST /api/v1/set_dissolve_pattern`

**Test Case**: Set dissolve pattern by ID
```python
Request Body:
{
    "pattern_id": 3
}
```

##### 3.4.3 Set Dissolve Time Test
**Endpoint**: `POST /api/v1/set_dissolve_time`

**Test Case**: Set dissolve time (milliseconds)
```python
Request Body:
{
    "time_ms": 2000
}
```

## Error Handling & Logging

### Logging System Overview
LED Animation Engine sử dụng structured logging với color support và performance optimization:

#### Component Colors (in terminal)
- **AnimationEngine**: BLUE
- **SceneManager**: MAGENTA  
- **LEDOutput**: YELLOW
- **OSCHandler**: CYAN
- **PerformanceMonitor**: WHITE

#### Log Format
```
[timestamp] [LEVEL] [Component]: message
```

#### Log Levels with Colors
- **DEBUG**: CYAN
- **INFO**: GREEN
- **WARNING**: YELLOW
- **ERROR**: RED
- **CRITICAL**: RED + WHITE background

### Log Level Messages

#### INFO Messages (GREEN color in terminal)
**OSC Messages**:
- `"Received OSC: {address} with args: {args}"`
- `"Processed {address} (result={result})"`
- `"OSC Server started successfully at {host}:{port}"`
- `"OSC Server is ready to receive messages"`

**Scene Management**:
- `"Scene {old_scene_id}→{scene_id}"`
- `"SceneManager initialized with zero-origin ID system"`
- `"JSON data loaded (type={json_type}, scenes_count={scenes_count})"`
- `"Parameter changed (parameter={param_name}, value={value})"`

**Animation Engine**:
- `"Animation Engine started successfully"`
- `"Animation loop started after loading scenes"`
- `"Waiting for JSON scenes to be loaded before starting animation loop"`
- `"Scene Manager initialization complete"`

**Performance Tracking**:
- `"PERFORMANCE: {operation} completed (duration_ms={duration:.2f})"`
- `"PERF {metric_name}: {value:.3f}{unit}"`

**Operations**:
- `"Palette {palette_id}[{color_id}] = RGB({r},{g},{b})"`
- `"Successfully changed effect to {effect_id} using {transition_type}"`
- `"Successfully changed palette to {palette_id} using {transition_type}"`
- `"Dissolve pattern set to {pattern_id}"`

#### WARNING Messages (YELLOW color in terminal)
**Scene Validation**:
- `"Scene {scene_id} not found. Available: {available_scenes}"`
- `"No active scene for palette change"`
- `"No active scene for effect change"`
- `"Cannot start transition: no active scene"`

**Parameter Validation**:
- `"Effect ID {effect_id} invalid. Available effects: {available_effects}"`
- `"Palette ID {palette_id} invalid. Available palettes: {available_palettes}"`
- `"Invalid palette ID {palette_id} (must be 0-4)"`
- `"Invalid color ID {color_id} (must be 0-5)"`
- `"Invalid RGB[{i}] = {value} (must be 0-255)"`

**Performance Warnings**:
- `"Frame processing exceeded target by {time:.1f}ms"`
- `"No palette handler is registered"`
- `"Unsupported OSC message: {address} with args: {args}"`

**Dissolve System**:
- `"Dissolve pattern {pattern_id} not found. Available: {available}"`
- `"Cannot start dissolve transition: no active scene"`
- `"No dissolve pattern {pattern_id} available"`

#### ERROR Messages (RED color in terminal)
**OSC Processing Errors**:
- `"Processing failed: {error_msg} (address={address})"`
- `"Validation failed for {address} (field={field_name}, value={value})"`
- `"Error in OSC handler: {e}"`
- `"Error handling palette message {address}: {e}"`

**Scene Management Errors**:
- `"Error switching scene: {e}"`
- `"Error setting effect: {e}"`
- `"Error setting palette: {e}"`
- `"Error updating palette color: {e}"`
- `"Error loading dissolve patterns: {e}"`
- `"Error starting dissolve transition: {e}"`

**Animation Engine Errors**:
- `"Error starting engine: {e}"`
- `"Error in animation loop frame: {e}"`
- `"FATAL ERROR in animation loop: {e}"`
- `"Error in _update_frame: {e}"`
- `"Error in state callback: {e}"`

**File I/O Errors**:
- `"Failed to load JSON from {file_path}"`
- `"Error loading JSON scenes: {load_error}"`
- `"Could not setup file logging: {e}"`

**LED Output Errors**:
- `"Failed to create LED client {index}: {e}"`
- `"Error starting OSC server: {e}"`

**Validation Errors**:
- `"VALIDATION: {error_msg} ({extra_str})"`
- `"Validation Error in {field_name}: {error_msg}"`
- `"Invalid effect ID: {args[0]} (must be an integer)"`
- `"Invalid palette ID: {args[0]} (must be an integer)"`

#### DEBUG Messages (CYAN color in terminal)
**Animation Debug**:
- `"Animation frame {frame_count}: {active_count}/{total_count} LEDs active"`
- `"Transition: {phase.value}, progress: {progress:.2f}"`
- `"Segments: {segment_info}"`
- `"OSC batch: {message_count} messages | Latest: {address} {args_str}"`

**Component Operations**:
- `"Added OSC handler for: {address}"`
- `"Processing palette: {address} palette_id={palette_id}, color_id={color_id}"`
- `"Calling palette handler..."`
- `"{operation_name}: {details}"`

#### CRITICAL Messages (RED + WHITE background in terminal)
**System Failures**:
- `"Animation loop traceback: {traceback}"`
- `"System component failed to initialize"`
- `"Memory allocation critical failure"`
- `"Hardware communication lost"`

## Specialized Loggers

### OSC Logger
**Purpose**: Track OSC message processing with high frequency optimization
**Key Features**:
- Message batching for performance
- Automatic error counting
- Address pattern validation

**Sample Messages**:
- `"OSC batch: {message_count} messages | Latest: {address} {args_str}"`
- `"OSC ERROR: {message}"`
- `"OSC {address} {args_str}"`

### Animation Logger
**Purpose**: Track animation system operations
**Key Features**:
- Scene change logging
- Parameter change tracking
- Performance metrics

**Sample Messages**:
- `"JSON data loaded (type={json_type}, scenes_count={scenes_count})"`
- `"Parameter changed (parameter={param_name}, value={value})"`
- `"Validation failed: {error_msg} (operation={operation})"`

### Performance Tracker
**Purpose**: Monitor system performance with timing data
**Key Features**:
- Context manager for automatic timing
- Extra data attachment
- Component-specific tracking

**Sample Messages**:
- `"PERFORMANCE: {operation} completed (duration_ms={duration:.2f})"`
- `"PERF {metric_name}: {value:.3f}{unit}"`

## Validation Error Patterns

### OSC Validation Errors
```python
# Address validation
"Validation failed for {address} (field={field_name}, value={value})"

# Parameter validation  
"Invalid effect ID: {args[0]} (must be an integer)"
"Invalid palette ID {palette_id} (must be 0-4)"
"Invalid color ID {color_id} (must be 0-5)"

# RGB validation
"Invalid RGB[{i}] = {value} (must be 0-255)"
```

### Scene Validation Errors
```python
# Scene existence
"Scene {scene_id} not found. Available: {available_scenes}"

# Effect/Palette availability
"Effect ID {effect_id} invalid. Available effects: {available_effects}"
"Palette ID {palette_id} invalid. Available palettes: {available_palettes}"

# State validation
"No active scene for palette change"
"Cannot start transition: no active scene"
```

### File I/O Validation Errors
```python
# File operations
"Failed to load JSON from {file_path}"
"Error loading JSON scenes: {load_error}"
"Could not setup file logging: {e}"
```

## Performance Logging

### Frame Performance
```python
# Normal operation
"Animation frame {frame_count}: {active_count}/{total_count} LEDs active"

# Performance warnings
"Frame processing exceeded target by {time:.1f}ms"

# Transition tracking
"Transition: {phase.value}, progress: {progress:.2f}"
```

### Component Performance
```python
# Operation timing
"PERFORMANCE: {operation} completed (duration_ms={duration:.2f})"

# Metrics
"PERF {metric_name}: {value:.3f}{unit}"

# Component stats
"Component: {component_name}, uptime: {uptime_seconds}s, ops: {operations}"
```

## Test Log Analysis

### Success Indicators
- `"Animation Engine started successfully"`
- `"OSC Server is ready to receive messages"`
- `"Processed {address} (result=success)"`
- `"Successfully changed effect to {effect_id}"`

### Warning Indicators
- `"Frame processing exceeded target"`
- `"No palette handler is registered"`
- `"Unsupported OSC message"`
- Parameter validation warnings

### Error Indicators
- `"FATAL ERROR in animation loop"`
- `"Processing failed: {error_msg}"`
- `"Validation failed for {address}"`
- `"Error in OSC handler"`

### Debug Information
- Animation frame status
- Transition progress
- Segment information
- OSC batch processing

## Multi-Language Support Testing

### Supported Languages
- **vi**: Vietnamese
- **en**: English
- **ja**: Japanese

## Performance Testing

### Performance Metrics
- **Response Time**: API response time
- **Throughput**: Requests/second
- **Memory Usage**: Memory consumption level
- **OSC Latency**: OSC communication delay

## Integration Testing

### End-to-End Test Scenarios
1. **Complete Scene Workflow**:
   - Load scene JSON → Change scene → Update palette → Change effect
   
2. **Dissolve Pattern Workflow**:
   - Load dissolve JSON → Set pattern → Set dissolve time
   
3. **Real-time Control Workflow**:
   - Set speed → Update brightness → Change colors
