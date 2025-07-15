"""
Test cases cho Scene Manager
"""

import pytest
import json
import sys
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.append(str(Path(__file__).parent.parent.parent))

from src.core.scene_manager import SceneManager
from src.models.scene import Scene
from src.models.effect import Effect
from src.models.segment import Segment


class TestSceneManager:
    """Test cases for SceneManager"""
    
    @pytest.fixture
    def scene_manager(self):
        """Fixture to create a SceneManager instance"""
        return SceneManager()
    
    @pytest.fixture
    def sample_scene_data(self):
        """Sample scene data for testing"""
        return {
            "name": "Test Scene",
            "description": "Scene for testing",
            "effects": [
                {
                    "id": "effect_001",
                    "type": "static_color",
                    "duration": 0,
                    "segments": [
                        {
                            "start": 0,
                            "end": 224,
                            "color": [255, 0, 0],
                            "brightness": 255
                        }
                    ]
                }
            ],
            "total_duration": 0,
            "loop": False
        }
    
    def test_initialization(self, scene_manager):
        """Test initialization of scene manager"""
        assert scene_manager is not None
        assert scene_manager.current_scene is None
        assert scene_manager.scenes == {}
    
    def test_load_scene_from_data(self, scene_manager, sample_scene_data):
        """Test load scene from data"""
        scene = scene_manager.load_scene_from_data(sample_scene_data)
        
        assert scene is not None
        assert scene.name == "Test Scene"
        assert scene.description == "Scene for testing"
        assert len(scene.effects) == 1
        assert scene.total_duration == 0
        assert not scene.loop
    
    def test_load_scene_from_file(self, scene_manager):
        """Test load scene from file"""
        scene_file = "src/data/scenes/scene_01.json"
        
        try:
            scene = scene_manager.load_scene_from_file(scene_file)
            assert scene is not None
            assert scene.name == "Scene 01 - Static Red"
            assert len(scene.effects) > 0
        except FileNotFoundError:
            pytest.skip("Scene file not found")
    
    def test_add_and_get_scene(self, scene_manager, sample_scene_data):
        """Test add and get scene"""
        scene = scene_manager.load_scene_from_data(sample_scene_data)
        scene_id = "test_scene_001"
        
        scene_manager.add_scene(scene_id, scene)
        assert scene_id in scene_manager.scenes
        
        retrieved_scene = scene_manager.get_scene(scene_id)
        assert retrieved_scene == scene
        
        assert scene_manager.get_scene("non_existent") is None
    
    def test_remove_scene(self, scene_manager, sample_scene_data):
        """Test xóa scene"""
        scene = scene_manager.load_scene_from_data(sample_scene_data)
        scene_id = "test_scene_002"
        
        scene_manager.add_scene(scene_id, scene)
        assert scene_id in scene_manager.scenes
        
        scene_manager.remove_scene(scene_id)
        assert scene_id not in scene_manager.scenes
    
    def test_set_current_scene(self, scene_manager, sample_scene_data):
        """Test set current scene"""
        scene = scene_manager.load_scene_from_data(sample_scene_data)
        scene_id = "test_scene_003"
        
        scene_manager.add_scene(scene_id, scene)
        scene_manager.set_current_scene(scene_id)
        
        assert scene_manager.current_scene == scene
        
        scene_manager.set_current_scene("non_existent")
        assert scene_manager.current_scene == scene 
    
    def test_list_scenes(self, scene_manager, sample_scene_data):
        """Test list all scenes"""
        for i in range(3):
            scene_data = sample_scene_data.copy()
            scene_data["name"] = f"Test Scene {i}"
            scene = scene_manager.load_scene_from_data(scene_data)
            scene_manager.add_scene(f"scene_{i}", scene)
        
        scenes = scene_manager.list_scenes()
        assert len(scenes) == 3
        assert "scene_0" in scenes
        assert "scene_1" in scenes
        assert "scene_2" in scenes
    
    def test_get_scene_info(self, scene_manager, sample_scene_data):
        """Test get scene information"""
        scene = scene_manager.load_scene_from_data(sample_scene_data)
        scene_id = "test_scene_004"
        
        scene_manager.add_scene(scene_id, scene)
        scene_manager.set_current_scene(scene_id)
        
        info = scene_manager.get_scene_info()
        
        assert info["scene_id"] == scene_id
        assert info["scene_name"] == "Test Scene"
        assert info["total_effects"] == 1
        assert info["total_duration"] == 0
        assert "current_effect" in info
    
    def test_validate_scene_data(self, scene_manager):
        """Test validation of scene data"""
        valid_data = {
            "name": "Valid Scene",
            "effects": [
                {
                    "id": "effect_001",
                    "type": "static_color",
                    "duration": 1000,
                    "segments": [
                        {
                            "start": 0,
                            "end": 10,
                            "color": [255, 0, 0]
                        }
                    ]
                }
            ],
            "total_duration": 1000,
            "loop": False
        }
        
        scene = scene_manager.load_scene_from_data(valid_data)
        assert scene is not None
        
        invalid_data = {
            "name": "Invalid Scene"
        }
        
        with pytest.raises((KeyError, ValueError)):
            scene_manager.load_scene_from_data(invalid_data)
    
    def test_scene_effects_processing(self, scene_manager, sample_scene_data):
        """Test processing of effects in a scene"""
        complex_scene_data = {
            "name": "Complex Scene",
            "effects": [
                {
                    "id": "effect_001",
                    "type": "static_color",
                    "duration": 1000,
                    "segments": [
                        {
                            "start": 0,
                            "end": 50,
                            "color": [255, 0, 0],
                            "brightness": 255
                        }
                    ]
                },
                {
                    "id": "effect_002",
                    "type": "fade",
                    "duration": 2000,
                    "segments": [
                        {
                            "start": 51,
                            "end": 100,
                            "color_start": [0, 0, 0],
                            "color_end": [0, 255, 0],
                            "brightness": 200
                        }
                    ]
                }
            ],
            "total_duration": 3000,
            "loop": True
        }
        
        scene = scene_manager.load_scene_from_data(complex_scene_data)
        assert len(scene.effects) == 2
        assert scene.total_duration == 3000
        assert scene.loop
        
        effects = scene.effects
        assert effects[0].id == "effect_001"
        assert effects[0].type == "static_color"
        assert effects[1].id == "effect_002"
        assert effects[1].type == "fade"


class TestSceneDataStructures:
    """Test Scene data structures"""
    
    def test_scene_creation(self):
        """Test creating a Scene object"""
        effects = [
            Effect(
                id="test_effect",
                type="static_color",
                duration=1000,
                segments=[
                    Segment(start=0, end=10, color=[255, 0, 0])
                ]
            )
        ]
        
        scene = Scene(
            name="Test Scene",
            description="Test description",
            effects=effects,
            total_duration=1000,
            loop=False
        )
        
        assert scene.name == "Test Scene"
        assert scene.description == "Test description"
        assert len(scene.effects) == 1
        assert scene.total_duration == 1000
        assert not scene.loop
    
    def test_effect_creation(self):
        """Test tạo Effect object"""
        segments = [
            Segment(start=0, end=10, color=[255, 0, 0]),
            Segment(start=11, end=20, color=[0, 255, 0])
        ]
        
        effect = Effect(
            id="test_effect",
            type="rainbow",
            duration=2000,
            segments=segments
        )
        
        assert effect.id == "test_effect"
        assert effect.type == "rainbow"
        assert effect.duration == 2000
        assert len(effect.segments) == 2
    
    def test_segment_creation(self):
        """Test tạo Segment object"""
        segment = Segment(
            start=0,
            end=10,
            color=[255, 128, 64],
            brightness=200
        )
        
        assert segment.start == 0
        assert segment.end == 10
        assert segment.color == [255, 128, 64]
        assert segment.brightness == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 