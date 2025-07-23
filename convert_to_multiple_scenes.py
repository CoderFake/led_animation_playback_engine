import json
import sys
from pathlib import Path
from typing import Dict, List, Any

def convert_old_format_to_multiple_scenes(old_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert old JSON format to new multiple_scenes format
    
    Args:
        old_data: Original JSON data with old format
        
    Returns:
        Converted data in multiple_scenes format
    """
    
    scene_id = old_data.get("scene_ID", 0) - 1 
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
        effect_id = effect_data.get("effect_ID", int(effect_key)) - 1 
        led_count = effect_data.get("led_count", 205)
        fps = effect_data.get("fps", 60)
        
        segments_dict = effect_data.get("segments", {})
        converted_segments = {}
        
        sorted_segment_items = sorted(segments_dict.items(), key=lambda x: int(x[0]))
        
        for seg_key, seg_data in sorted_segment_items:
            segment_id = seg_data.get("segment_ID", int(seg_key)) - 1 
            
            converted_segment = {
                "segment_id": segment_id,
                "color": seg_data.get("color", [0]),
                "transparency": seg_data.get("transparency", [1.0]),
                "length": seg_data.get("length", [1]),
                "move_speed": float(seg_data.get("move_speed", 0)),
                "move_range": seg_data.get("move_range", [0, 0]),
                "initial_position": seg_data.get("initial_position", 0),
                "current_position": float(seg_data.get("current_position", 0)),
                "is_edge_reflect": seg_data.get("is_edge_reflect", True)
            }
            
            dimmer_time_old = seg_data.get("dimmer_time", [0, 0, 100, 100, 100])
            
            if len(dimmer_time_old) >= 5:
                start_time, fade_in_time, on_time, fade_out_time, end_time = dimmer_time_old[:5]
                
                dimmer_time_new = []
                
                if fade_in_time > start_time:
                    dimmer_time_new.append([fade_in_time - start_time, 0, 100])
                
                if on_time > fade_in_time:
                    dimmer_time_new.append([on_time - fade_in_time, 100, 100])
                
                if fade_out_time > on_time:
                    dimmer_time_new.append([fade_out_time - on_time, 100, 0])
                
                if not dimmer_time_new:
                    dimmer_time_new = [[100, 100, 100]]
            else:
                dimmer_time_new = [[100, 100, 100]]
            
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
        print("Example: python convert_to_multiple_scenes.py 03_summer_250710a.json")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    success = convert_file(input_file, output_file)
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()