"""
LED Output
High-performance LED data transmission via OSC
"""

import struct
import time
import threading
from typing import List, Dict, Any, Optional
from pythonosc import udp_client
from collections import deque

from config.settings import EngineSettings
from src.utils.logger import ComponentLogger
from src.utils.performance import ProfileTimer

logger = ComponentLogger("LEDOutput")


class LEDDestination:
    """
    Individual LED output destination
    """
    
    def __init__(self, config: Dict[str, Any], index: int):
        self.index = index
        self.ip = config.get("ip", "127.0.0.1")
        self.port = config.get("port", 7000)
        self.enabled = config.get("enabled", True)
        self.name = config.get("name", f"Device_{index}")
        
        self.client: Optional[udp_client.SimpleUDPClient] = None
        self.send_count = 0
        self.error_count = 0
        self.last_send_time = 0.0
        self.connection_status = "disconnected"
        
        self.performance_timer = ProfileTimer(f"led_output_{index}")
        
        if self.enabled:
            self._initialize_client()
    
    def _initialize_client(self):
        """Initialize OSC client for this destination"""
        try:
            self.client = udp_client.SimpleUDPClient(self.ip, self.port)
            self.connection_status = "connected"
            logger.info(f"LED serial output {self.index} ({self.name}) connected to {self.ip}:{self.port}")
        except Exception as e:
            self.connection_status = "error"
            logger.error(f"Failed to create LED client {self.index}: {e}")
    
    def send_data(self, address: str, data: bytes) -> bool:
        """Send LED data to this destination"""
        if not self.enabled or not self.client:
            return False
        
        try:
            with self.performance_timer:
                self.client.send_message(address, data)
                
            self.send_count += 1
            self.last_send_time = time.time()
            self.connection_status = "active"
            return True
            
        except Exception as e:
            self.error_count += 1
            self.connection_status = "error"
            logger.error(f"Error sending to destination {self.index} ({self.ip}:{self.port}): {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get destination statistics"""
        return {
            "index": self.index,
            "name": self.name,
            "ip": self.ip,
            "port": self.port,
            "enabled": self.enabled,
            "connected": self.client is not None,
            "status": self.connection_status,
            "send_count": self.send_count,
            "error_count": self.error_count,
            "last_send_time": self.last_send_time,
            "performance": self.performance_timer.get_stats()
        }
    
    def reset_stats(self):
        """Reset statistics"""
        self.send_count = 0
        self.error_count = 0
        self.performance_timer.total_time = 0.0
        self.performance_timer.call_count = 0


class LEDOutput:
    """
    High-performance LED output system via OSC
    Handles multiple destinations with comprehensive monitoring
    """
    
    def __init__(self):
        self.destinations: List[LEDDestination] = []
        self.output_enabled = True
        
        self.send_count = 0
        self.last_send_time = 0.0
        self.send_interval = 1.0 / 60.0
        self.error_count = 0
        
        self.fps_frame_count = 0
        self.fps_start_time = 0.0
        self.actual_send_fps = 0.0
        self.fps_history = deque(maxlen=120)
        
        self.data_conversion_timer = ProfileTimer("data_conversion")
        self.broadcast_timer = ProfileTimer("broadcast")
        
        self._lock = threading.RLock()
        
        self.stats = {
            'total_sends': 0,
            'successful_sends': 0,
            'failed_sends': 0,
            'bytes_sent': 0,
            'destinations_active': 0,
            'last_data_size': 0
        }
        
    async def start(self):
        """
        Initialize LED output destinations
        """
        try:
            logger.info("Starting LED Output system...")
            
            self.destinations.clear()
            destinations_config = EngineSettings.get_led_destinations()
            
            if not destinations_config:
                logger.warning("No LED serial outputs configured")
                return
            
            logger.info(f"Configuring {len(destinations_config)} LED serial outputs...")
            
            active_count = 0
            for i, destination_config in enumerate(destinations_config):
                try:
                    if hasattr(destination_config, 'ip'):
                        config_dict = {
                            "ip": destination_config.ip,
                            "port": destination_config.port,
                            "enabled": destination_config.enabled,
                            "name": destination_config.name or f"Device_{i}"
                        }
                    else:
                        config_dict = destination_config
                    
                    destination = LEDDestination(config_dict, i)
                    self.destinations.append(destination)
                    
                    if destination.enabled and destination.client:
                        active_count += 1
                        
                except Exception as e:
                    logger.error(f"Error creating destination {i}: {e}")
                    
            self.fps_start_time = time.time()
            self.fps_frame_count = 0
            
            with self._lock:
                self.stats['destinations_active'] = active_count
            
            logger.info(f"LED Output started: {active_count}/{len(self.destinations)} destinations active")
            
            if active_count == 0:
                logger.warning("No active LED serial outputs - output will be disabled")
                self.output_enabled = False
            
        except Exception as e:
            logger.error(f"Error starting LED output: {e}")
            raise
    
    async def stop(self):
        """
        Stop LED output and cleanup
        """
        logger.info("Stopping LED Output system...")
        
        self.output_enabled = False
        
        with self._lock:
            for destination in self.destinations:
                destination.client = None
                destination.connection_status = "disconnected"
            
            self.destinations.clear()
        
        final_stats = self.get_stats()
        logger.info(f"LED Output stopped - Total sends: {final_stats['send_count']}, Errors: {final_stats['error_count']}")
    
    def send_led_data(self, led_colors: List[List[int]]):
        """
        Send LED color data to all active destinations
        """
        if not self.output_enabled or not led_colors:
            return
        
        current_time = time.time()
        
        try:
            with self._lock:
                with self.data_conversion_timer:
                    binary_data = self._convert_to_binary(led_colors)
                
                if not binary_data:
                    logger.warning("Failed to convert LED data to binary")
                    return
                
                with self.broadcast_timer:
                    successful_sends = self._broadcast_data(binary_data)
                
                self._update_statistics(current_time, len(binary_data), successful_sends)
                
                if successful_sends > 0:
                    self.send_count += 1
                    self.last_send_time = current_time
                    self._update_fps_tracking(current_time)
                
        except Exception as e:
            self.error_count += 1
            logger.error(f"Error in send_led_data: {e}")
    
    def _convert_to_binary(self, led_colors: List[List[int]]) -> bytes:
        """
        Convert LED colors to optimized binary format
        """
        try:
            if not led_colors:
                return b""
            
            binary_data = bytearray()
            
            for color in led_colors:
                if len(color) >= 3:
                    r = max(0, min(255, int(color[0])))
                    g = max(0, min(255, int(color[1])))
                    b = max(0, min(255, int(color[2])))
                else:
                    r = g = b = 0
                
                binary_data.extend(struct.pack("BBBB", r, g, b, 0))
            
            return bytes(binary_data)
            
        except Exception as e:
            logger.error(f"Error converting LED data to binary: {e}")
            return b""
    
    def _broadcast_data(self, binary_data: bytes) -> int:
        """
        Broadcast data to all active destinations with range mode support
        """
        successful_sends = 0
        output_address = EngineSettings.OSC.output_address
        
        led_count = len(binary_data) // 4
        
        for destination in self.destinations:
            if not destination.enabled or not destination.client:
                continue
                
            dest_config = self._get_destination_config(destination.index)
            if not dest_config:
                data_to_send = binary_data
            else:
                if dest_config.copy_mode:
                    data_to_send = binary_data
                else:
                    data_to_send = self._extract_led_range(
                        binary_data, led_count, 
                        dest_config.start_led, dest_config.end_led
                    )
            
            if destination.send_data(output_address, data_to_send):
                successful_sends += 1
        
        return successful_sends
    
    def _get_destination_config(self, dest_index: int):
        """Get destination configuration from settings"""
        try:
            destinations_config = EngineSettings.get_led_destinations()
            if dest_index < len(destinations_config):
                return destinations_config[dest_index]
            return None
        except Exception:
            return None
    
    def _extract_led_range(self, binary_data: bytes, led_count: int, start_led: int, end_led: int) -> bytes:
        """Extract LED range with enhanced safety for large arrays"""
        try:
            if not binary_data:
                return b""
            
            actual_led_count = len(binary_data) // 4
            if actual_led_count == 0:
                return b""
            
            if end_led == -1:
                end_led = actual_led_count - 1
            
            start_led = max(0, min(start_led, actual_led_count - 1))
            end_led = max(start_led, min(end_led, actual_led_count - 1))
            
            start_byte = start_led * 4
            end_byte = (end_led + 1) * 4
            
            if start_byte >= len(binary_data):
                return b""
            
            end_byte = min(end_byte, len(binary_data))
            
            return binary_data[start_byte:end_byte]
            
        except Exception as e:
            logger.error(f"Error extracting LED range [{start_led}:{end_led}]: {e}")
            return b""
    
    def _update_statistics(self, current_time: float, data_size: int, successful_sends: int):
        """
        Update internal statistics
        """
        with self._lock:
            self.stats['total_sends'] += len(self.destinations)
            self.stats['successful_sends'] += successful_sends
            self.stats['failed_sends'] += (len(self.destinations) - successful_sends)
            self.stats['bytes_sent'] += data_size * successful_sends
            self.stats['last_data_size'] = data_size
            self.stats['destinations_active'] = sum(1 for d in self.destinations if d.enabled and d.client)
    
    def _update_fps_tracking(self, current_time: float):
        """
        Update FPS tracking and logging
        """
        self.fps_frame_count += 1
        
        if self.fps_frame_count >= 300: 
            fps_time_diff = current_time - self.fps_start_time
            
            if fps_time_diff > 0:
                self.actual_send_fps = self.fps_frame_count / fps_time_diff
                self.fps_history.append(self.actual_send_fps)
                logger.info(f"LED Output: {self.actual_send_fps:.2f} FPS, Sends: {self.send_count}, Errors: {self.error_count}")
            
            self.fps_start_time = current_time
            self.fps_frame_count = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive output statistics
        """
        with self._lock:
            active_destinations = sum(1 for d in self.destinations if d.enabled and d.client)
            
            avg_fps = 0.0
            if self.fps_history:
                avg_fps = sum(self.fps_history) / len(self.fps_history)
            
            return {
                "enabled": self.output_enabled,
                "total_devices": len(self.destinations),
                "active_devices": active_destinations,
                "send_count": self.send_count,
                "error_count": self.error_count,
                "last_send_time": self.last_send_time,
                "actual_send_fps": self.actual_send_fps,
                "average_send_fps": avg_fps,
                "target_fps": 60.0,
                "data_conversion_avg_ms": self.data_conversion_timer.get_average_time() * 1000,
                "broadcast_avg_ms": self.broadcast_timer.get_average_time() * 1000,
                **self.stats,
                "destinations": [dest.get_stats() for dest in self.destinations]
            }