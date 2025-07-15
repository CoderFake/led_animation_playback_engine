"""
Test cases for OSC Handler
"""

import pytest
import asyncio
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add src to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.core.osc_handler import OSCHandler
from config.settings import EngineSettings


class TestOSCHandler:
    """Test cases for OSCHandler"""
    
    @pytest.fixture
    def mock_engine(self):
        """Mock AnimationEngine"""
        engine = Mock()
        engine.set_brightness = Mock()
        engine.set_speed = Mock()
        engine.load_scene_from_file = Mock()
        engine.get_stats = Mock()
        engine.get_scene_info = Mock()
        return engine
    
    @pytest.fixture
    def osc_handler(self, mock_engine):
        """Fixture to create an OSCHandler instance"""
        handler = OSCHandler(mock_engine)
        return handler
    
    def test_initialization(self, osc_handler, mock_engine):
        """Test initialization of OSC handler"""
        assert osc_handler.engine == mock_engine
        assert not osc_handler.running
        assert osc_handler.server is None
        assert osc_handler.client is not None
    
    @pytest.mark.asyncio
    async def test_start_stop(self, osc_handler):
        """Test start/stop OSC server"""
        test_port = 8999
        with patch.object(EngineSettings.OSC, 'input_port', test_port):
            try:
                await osc_handler.start()
                assert osc_handler.running
                assert osc_handler.server is not None
                
                await osc_handler.stop()
                assert not osc_handler.running
            except OSError:
                pytest.skip("Port already in use")
    
    def test_brightness_handler(self, osc_handler, mock_engine):
        """Test OSC brightness handler"""
        osc_handler._handle_brightness(None, 128)
        mock_engine.set_brightness.assert_called_once_with(128)
        
        mock_engine.reset_mock()
        osc_handler._handle_brightness(None, 0.5) 
        mock_engine.set_brightness.assert_called_once_with(127)
    
    def test_speed_handler(self, osc_handler, mock_engine):
        """Test OSC speed handler"""
        osc_handler._handle_speed(None, 75.0)
        mock_engine.set_speed.assert_called_once_with(75.0)
        
        mock_engine.reset_mock()
        osc_handler._handle_speed(None, 0.8)  
        mock_engine.set_speed.assert_called_once_with(80.0) 
    
    def test_scene_handler(self, osc_handler, mock_engine):
        """Test OSC scene handler"""
        osc_handler._handle_scene(None, 1)
        expected_file = f"src/data/scenes/scene_{1:02d}.json"
        mock_engine.load_scene_from_file.assert_called_once_with(expected_file)
        
        mock_engine.reset_mock()
        osc_handler._handle_scene(None, "test_scene")
        mock_engine.load_scene_from_file.assert_called_once_with("test_scene")
    
    def test_status_handler(self, osc_handler, mock_engine):
        """Test OSC status handler"""
        mock_stats = Mock()
        mock_stats.total_leds = 225
        mock_stats.active_leds = 100
        mock_stats.frame_count = 1000
        mock_stats.actual_fps = 60.0
        mock_engine.get_stats.return_value = mock_stats
        
        mock_scene_info = {"scene_id": 1, "effect_id": 1}
        mock_engine.get_scene_info.return_value = mock_scene_info
        
        with patch.object(osc_handler, 'send_osc_message') as mock_send:
            osc_handler._handle_status(None)
            
            assert mock_send.call_count >= 2
            mock_engine.get_stats.assert_called_once()
            mock_engine.get_scene_info.assert_called_once()
    
    def test_send_osc_message(self, osc_handler):
        """Test sending OSC message"""
        with patch.object(osc_handler.client, 'send') as mock_send:
            osc_handler.send_osc_message("/test", 123, "hello")
            
            mock_send.assert_called_once()
            args = mock_send.call_args[0]
            assert "/test" in str(args[0])  
    
    def test_message_routing(self, osc_handler):
        """Test routing các OSC message""" 
        dispatcher = osc_handler.dispatcher
        
        brightness_handler = dispatcher._address_handlers.get("/led/brightness")
        speed_handler = dispatcher._address_handlers.get("/led/speed")
        scene_handler = dispatcher._address_handlers.get("/led/scene")
        status_handler = dispatcher._address_handlers.get("/led/status")
        
        assert brightness_handler is not None
        assert speed_handler is not None
        assert scene_handler is not None
        assert status_handler is not None
    
    def test_error_handling(self, osc_handler, mock_engine):
        """Test error handling in OSC handlers"""
        mock_engine.set_brightness.side_effect = ValueError("Invalid brightness")
        
        try:
            osc_handler._handle_brightness(None, "invalid")
        except Exception:
            pytest.fail("Handler should not raise exception")
        
        mock_engine.reset_mock()
        mock_engine.load_scene_from_file.side_effect = FileNotFoundError("Scene not found")
        
        try:
            osc_handler._handle_scene(None, 999)
        except Exception:
            pytest.fail("Handler should not raise exception")


class TestOSCIntegration:
    """Integration tests for OSC communication"""
    
    @pytest.mark.asyncio
    async def test_osc_client_server_communication(self):
        """Test communication between OSC client and server"""
        from pythonosc import udp_client
        from pythonosc.dispatcher import Dispatcher
        from pythonosc.osc_server import ThreadingOSCUDPServer
        import threading
        import time
        
        test_port = 9999
        received_messages = []
        
        def message_handler(address, *args):
            received_messages.append((address, args))
        
        dispatcher = Dispatcher()
        dispatcher.map("/test/*", message_handler)
        
        try:
            server = ThreadingOSCUDPServer(("127.0.0.1", test_port), dispatcher)
            server_thread = threading.Thread(target=server.serve_forever)
            server_thread.daemon = True
            server_thread.start()
            
            client = udp_client.SimpleUDPClient("127.0.0.1", test_port)
            
            time.sleep(0.1)  
            client.send_message("/test/hello", ["world", 123])
            time.sleep(0.1)  
            
            assert len(received_messages) > 0
            address, args = received_messages[0]
            assert address == "/test/hello"
            assert args == ("world", 123)
            
            server.shutdown()
            
        except OSError:
            pytest.skip("Test port already in use")


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 