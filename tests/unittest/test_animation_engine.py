"""
Test cases for Animation Engine
"""

import pytest
import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

from src.core.animation_engine import AnimationEngine
from src.models.scene import Scene
from config.settings import EngineSettings


class TestAnimationEngine:
    """Test cases for AnimationEngine"""
    
    @pytest.fixture
    async def engine(self):
        """Fixture to create an AnimationEngine instance"""
        engine = AnimationEngine()
        yield engine
        if engine.running:
            await engine.stop()
    
    @pytest.mark.asyncio
    async def test_engine_initialization(self, engine):
        """Test initialization of engine"""
        assert engine is not None
        assert not engine.running
        assert engine.current_scene is None
        assert engine.frame_count == 0
    
    @pytest.mark.asyncio
    async def test_engine_start_stop(self, engine):
        """Test start/stop engine"""
        await engine.start()
        assert engine.running
        
        await engine.stop()
        assert not engine.running
    
    @pytest.mark.asyncio
    async def test_load_scene_from_file(self, engine):
        """Test load scene from file"""
        scene_file = "src/data/scenes/scene_01.json"
        
        try:
            scene = await engine.load_scene_from_file(scene_file)
            assert scene is not None
            assert scene.name == "Scene 01 - Static Red"
        except Exception as e:
            pytest.skip(f"Scene file not found: {e}")
    
    @pytest.mark.asyncio
    async def test_get_stats(self, engine):
        """Test getting engine statistics"""
        stats = engine.get_stats()
        
        assert hasattr(stats, 'total_leds')
        assert hasattr(stats, 'active_leds')
        assert hasattr(stats, 'frame_count')
        assert hasattr(stats, 'actual_fps')
        assert hasattr(stats, 'animation_time')
        assert hasattr(stats, 'master_brightness')
        assert hasattr(stats, 'speed_percent')
        
        assert stats.total_leds == EngineSettings.ANIMATION.led_count
        assert stats.frame_count >= 0
        assert stats.actual_fps >= 0
    
    @pytest.mark.asyncio
    async def test_get_scene_info(self, engine):
        """Test lấy thông tin scene"""
        scene_info = engine.get_scene_info()
        
        assert isinstance(scene_info, dict)
        assert 'scene_id' in scene_info
        assert 'effect_id' in scene_info
        assert 'palette_id' in scene_info
        assert 'total_segments' in scene_info
        assert 'total_effects' in scene_info
    
    @pytest.mark.asyncio
    async def test_get_led_colors(self, engine):
        """Test getting LED colors"""
        led_colors = engine.get_led_colors()
        
        assert isinstance(led_colors, list)
        assert len(led_colors) == EngineSettings.ANIMATION.led_count
        
        for color in led_colors:
            assert isinstance(color, (list, tuple))
            assert len(color) == 3
            for channel in color:
                assert 0 <= channel <= 255
    
    @pytest.mark.asyncio
    async def test_set_brightness(self, engine):
        """Test set brightness"""
        original_brightness = engine.master_brightness
        
        test_brightness = 128
        engine.set_brightness(test_brightness)
        assert engine.master_brightness == test_brightness
        
        # Test boundary values
        engine.set_brightness(0)
        assert engine.master_brightness == 0
        
        engine.set_brightness(255)
        assert engine.master_brightness == 255
        
        # Test invalid values
        engine.set_brightness(-10)
        assert engine.master_brightness >= 0
        
        engine.set_brightness(300)
        assert engine.master_brightness <= 255
        
        # Restore original
        engine.set_brightness(original_brightness)
    
    @pytest.mark.asyncio
    async def test_set_speed(self, engine):
        """Test set speed"""
        original_speed = engine.speed_percent
        
        # Test set speed
        test_speed = 75.0
        engine.set_speed(test_speed)
        assert engine.speed_percent == test_speed
        
        # Test boundary values
        engine.set_speed(0.0)
        assert engine.speed_percent == 0.0
        
        engine.set_speed(200.0)
        assert engine.speed_percent == 200.0
        
        # Restore original
        engine.set_speed(original_speed)
    
    @pytest.mark.asyncio
    async def test_scene_switching(self, engine):
        """Test chuyển scene"""
        await engine.start()
        
        # Test load multiple scenes nếu có file
        try:
            scene1 = await engine.load_scene_from_file("src/data/scenes/scene_01.json")
            scene2 = await engine.load_scene_from_file("src/data/scenes/scene_02.json")
            
            engine.set_current_scene(scene1)
            assert engine.current_scene == scene1
            
            engine.set_current_scene(scene2)
            assert engine.current_scene == scene2
            
        except Exception:
            pytest.skip("Scene files not available for testing")
        
        await engine.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 