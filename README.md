# LED Animation Playback Engine

A high-performance LED animation system with OSC control, real-time rendering, and multi-device output support.

## Overview

The LED Animation Playback Engine is a comprehensive system for generating and controlling LED animations in real-time. It supports:

- **Real-time LED animation rendering** at configurable FPS (1-240 FPS)
- **OSC (Open Sound Control) protocol** for remote control
- **Multi-device output** with full copy or range-based distribution
- **Scene, Effect, and Palette management** with zero-origin ID system
- **Dissolve pattern transitions** for smooth scene changes
- **Multi-language API support** (Vietnamese, English, Japanese)
- **Comprehensive testing suite** with unit tests and API tests

## Features

### Core Features
- **Configurable FPS**: 1-240 FPS animation rendering
- **Multi-device Output**: Send to multiple LED controllers simultaneously
- **Copy/Range Modes**: Full data copy or specific LED range distribution
- **Time-based Dimmer**: Smooth brightness transitions over time
- **Fractional Positioning**: Sub-pixel positioning with fade effects
- **Extended Speed Range**: 0-1023% animation speed control
- **Dissolve Patterns**: Advanced transition effects between scenes
- **Performance Monitoring**: Real-time performance tracking and optimization

### Control Features
- **OSC Protocol**: Remote control via OSC messages
- **Real-time Parameter Control**: Speed, brightness, effects, palettes
- **Scene Management**: Load, switch, and manage multiple scenes
- **Palette Control**: Dynamic color palette manipulation

## Architecture

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

### Core Components

- **Animation Engine**: Main processor with configurable FPS loop
- **Scene Manager**: Manages Scene, Effect, Palette and transitions
- **Dissolve Manager**: Handles dissolve transition patterns
- **OSC Handler**: Processes input OSC messages
- **Multi-Device LED Output**: Distributes RGB data to multiple devices
- **Performance Monitor**: System performance tracking

## Installation

### Prerequisites

- Python `>=3.10, <3.12`
- pip package manager

### Dependencies

```bash
# Install main dependencies
pip install -r requirements.txt

# Install API test dependencies
pip install -r tests/apitest/requirements.txt
```

### Main Dependencies
- `python-osc`: OSC protocol support
- `pydantic`: Data validation and settings management
- `asyncio`: Asynchronous programming support
- `numpy`: High-performance array operations

### API Test Dependencies
- `fastapi`: Web framework for REST API
- `uvicorn`: ASGI server
- `httpx`: HTTP client for testing
- `pytest`: Testing framework

## Configuration

### Main Configuration

Edit `config/settings.py`:

```python
class AnimationConfig(BaseModel):
    target_fps: int = 60                    # Target FPS (1-240)
    led_count: int = 225                    # Default LED count
    master_brightness: int = 255            # Master brightness (0-255)
    
    led_destinations: List[LEDDestination] = [
        LEDDestination(
            ip="192.168.11.105", 
            port=7000, 
            copy_mode=True,                 # Full copy mode
            enabled=True
        ),
        LEDDestination(
            ip="192.168.11.106", 
            port=7001,
            start_led=0, 
            end_led=112,
            copy_mode=False,                # Range mode
            enabled=True
        )
    ]
```

### Multi-Device Configuration

**Copy Mode**: Send full LED data to device
```python
LEDDestination(ip="192.168.1.100", port=7000, copy_mode=True)
```

**Range Mode**: Send specific LED range to device
```python
LEDDestination(ip="192.168.1.101", port=7001, start_led=0, end_led=50, copy_mode=False)
```

### OSC Configuration

```python
class OSCConfig(BaseModel):
    input_host: str = "127.0.0.1"
    input_port: int = 8000
    output_address: str = "/light/serial"
```

## Usage

### Starting the Engine

```bash
# Start the main engine
python main.py

# Start with verbose logging
python main.py --verbose

# Start with specific configuration
python main.py --config custom_config.py
```

### Basic OSC Commands

```bash
# Load scene from JSON file
/load_json "scene_file.json"

# Change scene (zero-origin)
/change_scene 0

# Change effect
/change_effect 1

# Change palette
/change_palette 0

# Set animation speed (0-1023%)
/set_speed_percent 150

# Set master brightness (0-255)
/master_brightness 200

# Set dissolve transition time (milliseconds)
/set_dissolve_time 1500
```

### Scene JSON Format

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
        [
          [255, 0, 0],    // Red
          [0, 255, 0],    // Green
          [0, 0, 255]     // Blue
        ]
      ],
      "effects": [
        {
          "effect_id": 0,
          "segments": {
            "0": {
              "segment_id": 0,
              "color": [0, 1, 2],
              "transparency": [1.0, 0.8, 0.6],
              "length": [30, 30, 30],
              "move_speed": 50.0,
              "move_range": [0, 224],
              "dimmer_time": [
                [1000, 0, 100],    // [duration_ms, start_brightness, end_brightness]
                [2000, 100, 100],
                [1000, 100, 0]
              ]
            }
          }
        }
      ]
    }
  ]
}
```

### Multi-Point Segments

Support for flexible color point definitions:

```json
{
  "segment_id": 0,
  "color": [0, 1, 2, 3, 4, 5],           // 6 color points
  "transparency": [1.0, 1.0, 1.0, 1.0, 1.0, 1.0],
  "length": [30, 30, 30, 30, 30, 30]     // 6 length values
}
```

This creates:
- 30 LEDs with color[0]
- 30 LEDs with color[1]
- 30 LEDs with color[2]
- 30 LEDs with color[3]
- 30 LEDs with color[4]
- 30 LEDs with color[5]
- **Total: 180 LEDs**

## API Testing

### Starting the API Test Server

```bash
# Navigate to API test directory
cd tests/apitest

# Start the FastAPI server
python app.py

# Or use uvicorn directly
uvicorn app:app --host 0.0.0.0 --port 5001 --reload
```

### API Documentation

Access the interactive API documentation:

- **Swagger UI**: http://localhost:5001/docs
- **ReDoc**: http://localhost:5001/redoc
- **OpenAPI Schema**: http://localhost:5001/openapi.json

### Multi-Language Support

The API supports multiple languages:

- **Vietnamese**: http://localhost:5001/docs?lang=vi
- **English**: http://localhost:5001/docs?lang=en
- **Japanese**: http://localhost:5001/docs?lang=ja

### Available Endpoints

#### Scene Management
- `POST /api/v1/load_json` - Load scene from JSON file
- `POST /api/v1/change_scene` - Change to different scene

#### Palette Control
- `POST /api/v1/change_palette` - Change palette
- `POST /api/v1/palette/{palette_id}/{color_id}` - Update specific palette color

#### LED Control
- `POST /api/v1/change_effect` - Change effect
- `POST /api/v1/set_dissolve_time` - Set dissolve transition time
- `POST /api/v1/set_speed_percent` - Set animation speed
- `POST /api/v1/master_brightness` - Set master brightness

### Example API Requests

```bash
# Load scene
curl -X POST "http://localhost:5001/api/v1/load_json" \
  -H "Content-Type: application/json" \
  -d '{"file_path": "multiple_scenes.json"}'

# Change scene
curl -X POST "http://localhost:5001/api/v1/change_scene" \
  -H "Content-Type: application/json" \
  -d '{"scene_id": 1}'

# Set animation speed
curl -X POST "http://localhost:5001/api/v1/set_speed_percent" \
  -H "Content-Type: application/json" \
  -d '{"percent": 150}'

# Update palette color
curl -X POST "http://localhost:5001/api/v1/palette/0/0" \
  -H "Content-Type: application/json" \
  -d '{"r": 255, "g": 128, "b": 0}'
```

### Running API Tests

```bash
# Navigate to API test directory
cd tests/apitest

# Run all API tests
python -m pytest

# Run specific test file
python -m pytest test_endpoints.py

# Run with verbose output
python -m pytest -v

# Run with coverage
python -m pytest --cov=. --cov-report=html
```

## Unit Testing

### Running Unit Tests

```bash
# Navigate to unit test directory
cd tests/unittest

# Run all unit tests
python run_tests.py

# Run with verbose output
python run_tests.py --verbose

# Run specific test class
python -m unittest test_segment.TestSegment

# Run specific test method
python -m unittest test_segment.TestSegment.test_get_led_colors_with_timing
```

### Test Coverage

Current test coverage includes:

- **Color Utilities**: 12 test methods
- **Segment Logic**: 17 test methods  
- **Dissolve Patterns**: 12 test methods
- **Total**: 69 test methods

### Test Categories

#### Core Functionality Tests
- LED color generation and timing
- Segment rendering and positioning
- Brightness and transparency calculations
- Palette color mapping

#### Dissolve Pattern Tests
- Dissolve transition initialization
- LED timing setup with overlapping ranges
- Boundary clamping and validation
- Phase transitions and completion detection

#### Edge Case Tests
- Invalid input handling
- Boundary conditions
- Performance under load
- Error recovery

### Running Specific Test Suites

```bash
# Test color utilities only
python -c "
import unittest
from test_color_utils import TestColorUtils
suite = unittest.TestLoader().loadTestsFromTestCase(TestColorUtils)
runner = unittest.TextTestRunner(verbosity=2)
runner.run(suite)
"

# Test segment functionality only
python -c "
import unittest
from test_segment import TestSegment
suite = unittest.TestLoader().loadTestsFromTestCase(TestSegment)
runner = unittest.TextTestRunner(verbosity=2)
runner.run(suite)
"
```

### Performance Considerations

- The engine is optimized for real-time performance
- Frame processing should complete within target frame time
- Use profiling tools to identify bottlenecks
- Monitor memory usage for long-running operations
- Consider hardware limitations when setting FPS targets

### Testing Requirements

All contributions must include:
- Unit tests for new functionality
- API tests for new endpoints
- Documentation updates
- Performance impact assessment

## Support

For support and questions:
- Check the documentation in `docs/specs.md`

---