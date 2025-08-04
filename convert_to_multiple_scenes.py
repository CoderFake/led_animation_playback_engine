import json
import sys
from pathlib import Path
from typing import Dict, List, Any

def convert_dimmer_time(old_format: List[int]) -> List[List[int]]:
    """
    Convert old system (position-based) to new system (transition-based)
    
    Old: [fade_in_start, fade_in_end, fade_out_start, fade_out_end, cycle_length]
    New: [[duration, start_brightness, end_brightness]]
    """
    if not old_format or len(old_format) < 5:
        return [[100, 100, 100]]
    
    fade_in_start = old_format[0]
    fade_in_end = old_format[1] 
    fade_out_start = old_format[2]
    fade_out_end = old_format[3]
    cycle_length = old_format[4]
    
    if cycle_length <= 0:
        return [[100, 100, 100]]
    
    if fade_in_start == fade_in_end and fade_out_start == fade_out_end:
        if fade_in_end == 0 and fade_out_start >= cycle_length:
            return [[cycle_length, 100, 100]]
        
        new_format = []
        
        if fade_in_end > 0:
            new_format.append([fade_in_end, 0, 0])
        
        if fade_out_start > fade_in_end:
            new_format.append([fade_out_start - fade_in_end, 100, 100])
        
        if cycle_length > fade_out_start:
            new_format.append([cycle_length - fade_out_start, 0, 0])
            
        return new_format if new_format else [[cycle_length, 100, 100]]
    
    new_format = []
    current_time = 0
    
    if fade_in_start > current_time:
        new_format.append([fade_in_start - current_time, 0, 0])
        current_time = fade_in_start
    
    if fade_in_end > current_time:
        new_format.append([fade_in_end - current_time, 0, 100])
        current_time = fade_in_end
    
    if fade_out_start > current_time:
        new_format.append([fade_out_start - current_time, 100, 100])
        current_time = fade_out_start
    
    if fade_out_end > current_time:
        new_format.append([fade_out_end - current_time, 100, 0])
        current_time = fade_out_end
    
    if cycle_length > current_time:
        new_format.append([cycle_length - current_time, 0, 0])
    
    return new_format if new_format else [[cycle_length, 100, 100]]

def convert_old_format_to_multiple_scenes(old_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert old JSON format to new multiple_scenes format
    
    Args:
        old_data: Original JSON data with old format
        
    Returns:
        Converted data in multiple_scenes format
    """
    
    scene_id = old_data.get("scene_ID", 1) - 1
    current_effect_id = old_data.get("current_effect_ID", 1) - 1
    current_palette = old_data.get("current_palette", "A")
    
    palettes_dict = old_data.get("palettes", {})
    palettes_array = []
    
    palette_keys = sorted(palettes_dict.keys())
    current_palette_id = 0
    
    for i, key in enumerate(palette_keys):
        if key == current_palette:
            current_palette_id = i
        palettes_array.append(palettes_dict[key])
    
    effects_dict = old_data.get("effects", {})
    effects_array = []
    
    sorted_effect_items = sorted(effects_dict.items(), key=lambda x: int(x[0]))
    
    for effect_key, effect_data in sorted_effect_items:
        effect_id = int(effect_key) - 1
        
        segments_dict = effect_data.get("segments", {})
        converted_segments = {}
        
        sorted_segment_items = sorted(segments_dict.items(), key=lambda x: int(x[0]))
        
        for seg_key, seg_data in sorted_segment_items:
            segment_id = int(seg_key) - 1
            
            converted_segment = {
                "segment_id": segment_id,
                "color": seg_data.get("color", [0]),
                "transparency": [1.0 - float(t) for t in seg_data.get("transparency", [1.0])],
                "length": seg_data.get("length", [1]),
                "move_speed": float(seg_data.get("move_speed", 0)),
                "move_range": seg_data.get("move_range", [0, 224]),
                "initial_position": int(seg_data.get("initial_position", 0)),
                "current_position": int(seg_data.get("current_position", seg_data.get("initial_position", 0))),
                "is_edge_reflect": seg_data.get("is_edge_reflect", True)
            }
            
            dimmer_time_old = seg_data.get("dimmer_time", [0, 0, 100, 100, 100])
            dimmer_time_new = convert_dimmer_time(dimmer_time_old)
            converted_segment["dimmer_time"] = dimmer_time_new
            
            converted_segments[str(segment_id)] = converted_segment
        
        effect_obj = {
            "effect_id": effect_id,
            "segments": converted_segments
        }
        
        effects_array.append(effect_obj)
    
    first_effect = effects_dict.get("1", {}) if effects_dict else {}
    led_count = first_effect.get("led_count", 205)
    fps = first_effect.get("fps", 60)
    
    scene = {
        "scene_id": scene_id,
        "led_count": led_count,
        "fps": fps,
        "current_effect_id": current_effect_id,
        "current_palette_id": current_palette_id,
        "palettes": palettes_array,
        "effects": effects_array
    }
    
    result = {
        "scenes": [scene]
    }
    
    return result

def convert_file(input_file: str, output_file: str = None):
    """
    Convert JSON file from old format to multiple_scenes format
    
    Args:
        input_file: Path to input JSON file
        output_file: Path to output JSON file (optional)
    """
    
    input_path = Path(input_file)
    
    if not input_path.exists():
        print(f"Error: Input file '{input_file}' not found")
        return False
    
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            old_data = json.load(f)
    except Exception as e:
        print(f"Error reading input file: {e}")
        return False
    
    try:
        new_data = convert_old_format_to_multiple_scenes(old_data)
    except Exception as e:
        print(f"Error converting data: {e}")
        return False
    
    if output_file is None:
        output_file = input_path.stem + "_multiple_scenes.json"
    
    output_path = Path(output_file)
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(new_data, f, indent=2, ensure_ascii=False)
        
        print(f"Successfully converted '{input_file}' to '{output_file}'")
        print(f"Scenes count: {len(new_data['scenes'])}")
        
        scene = new_data['scenes'][0]
        print(f"Scene ID: {scene['scene_id']}")
        print(f"LED count: {scene['led_count']}")
        print(f"FPS: {scene['fps']}")
        print(f"Effects count: {len(scene['effects'])}")
        print(f"Palettes count: {len(scene['palettes'])}")
        
        return True
        
    except Exception as e:
        print(f"Error writing output file: {e}")
        return False

def main():
    """Main function to handle command line arguments"""
    
    if len(sys.argv) < 2:
        print("Usage: python convert_to_multiple_scenes.py <input_file> [output_file]")
        print("Example: python convert_to_multiple_scenes.py 02.flower_250722a.json")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    success = convert_file(input_file, output_file)
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()