# LED Animation Engine - Terminal Version

## Project Structure

```
led_animation_playback_engine/
    ├── main.py                     # Main entry point for terminal mode
    ├── requirements.txt            # Python dependencies
    ├── config/
    │   ├── __init__.py
    │   └── settings.py            # Engine configuration
    ├── src/
    │   ├── __init__.py
    │   ├── core/                  # Engine core components
    │   │   ├── __init__.py
    │   │   ├── animation_engine.py    # Main LED Animation Engine
    │   │   ├── scene_manager.py       # Scene management and transitions
    │   │   ├── led_output.py         # LED data output via OSC
    │   │   └── osc_handler.py        # OSC message input handler
    │   ├── models/                # Data models
    │   │   ├── __init__.py
    │   │   ├── scene.py          # Scene data model
    │   │   ├── effect.py         # Effect data model
    │   │   └── segment.py        # Segment data model
    │   ├── utils/                # Utility modules
    │   │   ├── __init__.py
    │   │   ├── logger.py         # Logging system
    │   │   └── performance.py    # Performance monitoring
    │   └── data/                 # Data files
    │       ├── scenes/           # Scene JSON files
    │       │   └── multiple_scenes.json
    │       └── logs/             # Log files directory
    ├── tests/                    # Unit tests
    └── docs/                     # Documentation
        └── README.md
```

## Features

### Core Features
- **LED Animation Playback Engine**: Real-time animation processing at 60 FPS
- **OSC Input/Output**: Receives control messages and sends LED data via OSC
- **Scene Management**: Load, switch, and manage multiple animation scenes
- **Pattern Transitions**: Smooth transitions between effects and palettes
- **Performance Monitoring**: Real-time FPS and performance statistics

### Control Features
- **Scene Switching**: Change between different animation scenes
- **Effect Control**: Switch effects within scenes
- **Palette Control**: Change color palettes and update individual colors
- **Animation Control**: Adjust speed, brightness, and dissolve time
- **Pattern Transitions**: Configurable fade-in/fade-out transitions

### Technical Features
- **Multi-threaded Architecture**: Separate threads for OSC, animation, and output
- **Thread-safe Operations**: Proper locking for concurrent access
- **Error Handling**: Comprehensive error handling and recovery
- **Logging System**: Structured logging with multiple levels
- **Performance Optimization**: Efficient LED calculation and output

## OSC API

### Input Messages (Control)
- `/load_json [path]` - Load scene data from JSON file
- `/change_scene [scene_id]` - Switch to specific scene
- `/change_effect [effect_id]` - Change current effect
- `/change_palette [palette_id]` - Change current palette
- `/palette/[A-E]/[0-5] [r] [g] [b]` - Update palette color
- `/master_brightness [0-255]` - Set master brightness
- `/set_speed_percent [0-200]` - Set animation speed percentage
- `/set_dissolve_time [ms]` - Set dissolve time for transitions
- `/pattern_transition [fade_in_ms] [fade_out_ms] [waiting_ms]` - Configure transitions

### Output Messages
- `/light/serial [binary_data]` - LED color data sent to devices

## Usage

### Basic Usage
```bash
python main.py

python main.py --verbose

python main.py --config custom_config.json
```

### Background Service
```bash
# Run as background service
nohup python main.py > engine.log 2>&1 &

# Check status
ps aux | grep main.py

# Stop service
pkill -f main.py
```

## Configuration

Configuration is handled via `config/settings.py`:

```python
class EngineSettings:
    OSC = OSCConfig(
        input_host="127.0.0.1",
        input_port=8000,
        output_address="/light/serial"
    )
    
    ANIMATION = AnimationConfig(
        target_fps=60,
        led_count=225,
        master_brightness=255,
        led_destinations=[
            {"ip": "192.168.11.105", "port": 7000}
        ]
    )
    
    PATTERN_TRANSITION = PatternTransitionConfig(
        enabled=True,
        default_fade_in_ms=100,
        default_fade_out_ms=100,
        default_waiting_ms=50
    )
```

## Performance

- **Target FPS**: 60 FPS animation processing
- **LED Count**: Support for up to 1000+ LEDs
- **Latency**: <10ms OSC message processing
- **Memory**: Optimized for long-running background operation
- **CPU**: Multi-threaded for efficient resource usage

## Monitoring

The engine provides comprehensive monitoring:

- Real-time FPS tracking
- LED activity statistics
- OSC message statistics
- Memory and CPU usage
- Error rate monitoring
- Performance bottleneck detection

## Dependencies

- `python-osc>=1.9.3` - OSC protocol support
- `pydantic>=2.5.0` - Data validation and settings
- `colorama>=0.4.6` - Terminal color support

## License

MIT License - See LICENSE file for details