"""
OSC Handler - Zero-origin IDs and expanded palette format
Handles incoming OSC messages with proper conversion between old and new formats
"""

import re
import asyncio
import time
import threading
from typing import Dict, Callable, List, Any
from pythonosc import dispatcher
from pythonosc.osc_server import ThreadingOSCUDPServer
from concurrent.futures import ThreadPoolExecutor

from config.settings import EngineSettings
from src.utils.logger import get_logger, OSCLogger
from src.utils.logging import OSCLogger as NewOSCLogger, PerformanceTracker
from src.utils.validation import ValidationUtils

logger = get_logger(__name__)
osc_logger = OSCLogger()


class OSCHandler:
    """
    Handles incoming OSC messages with zero-origin ID support and format conversion
    """
    
    def __init__(self, engine):
        self.engine = engine
        self.dispatcher = dispatcher.Dispatcher()
        self.server = None
        
        self.message_handlers: Dict[str, Callable] = {}
        self.palette_handler: Callable = None
        
        self.executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="OSC")
        
        self.handler_timeout = 5.0 
        
        self.message_count = 0
        self.error_count = 0
        self.last_message_time = 0
        
        self._lock = threading.Lock()
        
        self._setup_dispatcher()
    
    def _setup_dispatcher(self):
        """
        Set up the OSC dispatcher
        """
        self.dispatcher.set_default_handler(self._handle_unknown_message)
    
    def add_handler(self, address: str, handler: Callable):
        """
        Add a handler for an OSC address
        """
        self.message_handlers[address] = handler
        self.dispatcher.map(address, self._create_wrapper(address, handler))
    
    def add_palette_handler(self, handler: Callable):
        """
        Add a handler for palette color updates (supports both old and new formats)
        """
        self.palette_handler = handler
        
        palette_pattern_old = "/palette/*/*"
        self.dispatcher.map(palette_pattern_old, self._handle_palette_message)
    
    def _create_wrapper(self, address: str, handler: Callable):
        """
        Create a wrapper function for a handler with proper logging
        """
        def wrapper(osc_address: str, *args):
            try:
                with self._lock:
                    self.message_count += 1
                    self.last_message_time = time.time()
                
                NewOSCLogger.log_received(osc_address, list(args))
                
                if not ValidationUtils.validate_osc_address(osc_address):
                    NewOSCLogger.log_validation_failed(osc_address, "address", osc_address, "valid OSC address starting with /")
                    return
                
                future = self.executor.submit(self._safe_handler_call, handler, osc_address, *args)
                
            except Exception as e:
                with self._lock:
                    self.error_count += 1
                NewOSCLogger.log_error(osc_address, f"Error wrapping OSC message: {e}")
        
        return wrapper
    
    def _safe_handler_call(self, handler: Callable, osc_address: str, *args):
        """
        Call a handler safely with error handling
        """
        try:
            with PerformanceTracker("OSC", f"handler_{osc_address}") as tracker:
                handler(osc_address, *args)
                tracker.add_data("args_count", len(args))
                NewOSCLogger.log_processed(osc_address, "success")
                
        except Exception as e:
            with self._lock:
                self.error_count += 1
            NewOSCLogger.log_error(osc_address, f"Error in OSC handler: {e}")
    
    def _handle_palette_message(self, address: str, *args):
        """
        Handle OSC messages for palette color updates with format conversion
        Supports both formats:
        - Old: /palette/{A-E}/{0-5} int[3] (R,G,B)
        - New: /palette/{0-4}/{0-5} int[3] (R,G,B)
        """
        try:
            with self._lock:
                self.message_count += 1
                self.last_message_time = time.time()
            
            NewOSCLogger.log_received(address, list(args))
            
            match = re.match(r"/palette/([A-E0-4])/([0-5])", address)
            if not match:
                logger.error(f"Invalid palette address format: {address}")
                return
            
            palette_part, color_id_str = match.groups()
            
            if palette_part in ['A', 'B', 'C', 'D', 'E']:
                palette_id = ord(palette_part) - ord('A')
            else:
                palette_id = int(palette_part) 
            
            color_id = int(color_id_str)
            
            if len(args) < 3:
                logger.error(f"Palette message requires at least 3 RGB arguments, got {len(args)}")
                return
            
            try:
                rgb = [int(args[i]) for i in range(3)]
                original_rgb = rgb.copy()
                
                for i in range(3):
                    if rgb[i] < 0:
                        logger.warning(f"RGB[{i}] = {rgb[i]} < 0, adjusted to 0")
                        rgb[i] = 0
                    elif rgb[i] > 255:
                        logger.warning(f"RGB[{i}] = {rgb[i]} > 255, adjusted to 255")
                        rgb[i] = 255
                
                if original_rgb != rgb:
                    logger.info(f"RGB values were adjusted: {original_rgb} -> {rgb}")
                
            except ValueError as ve:
                logger.error(f"RGB values are not integers: {args[:3]} - {ve}")
                return
            
            if palette_id < 0 or palette_id > 4:
                logger.error(f"Invalid Palette ID {palette_id} (must be 0-4)")
                return
            
            if color_id < 0 or color_id > 5:
                logger.error(f"Invalid Color ID {color_id} (must be 0-5)")
                return
            
            logger.info(f"Valid palette message: palette_id={palette_id}, color_id={color_id}, RGB=({rgb[0]},{rgb[1]},{rgb[2]})")
            
            if self.palette_handler:
                future = self.executor.submit(
                    self._safe_palette_handler_call, 
                    self.palette_handler, address, palette_id, color_id, rgb
                )
            else:
                logger.warning("No palette handler is registered")
                
        except Exception as e:
            with self._lock:
                self.error_count += 1
            logger.error(f"Error in handle_palette_message {address}: {e}")
            osc_logger.log_error(f"Error handling palette message {address}: {e}")
    
    def _safe_palette_handler_call(self, handler: Callable, address: str, palette_id: int, color_id: int, rgb: List[int]):
        """
        Call palette handler safely with zero-origin int palette_id
        """
        try:
            start_time = time.time()
            
            handler(address, palette_id, color_id, rgb)
            
            process_time = time.time() - start_time
            logger.info(f"Palette handler completed in {process_time:.3f}s")
            
        except Exception as e:
            logger.error(f"Error in palette handler {address}: {e}")
            osc_logger.log_error(f"Error in palette handler {address}: {e}")
    
    def _handle_unknown_message(self, address: str, *args):
        """
        Handle unknown OSC messages
        """
        logger.warning(f"Unsupported OSC message: {address} with args: {args}")
        logger.info(f"Supported addresses: {list(self.message_handlers.keys())}")
        osc_logger.log_message(f"UNKNOWN: {address}", args)
    
    async def start(self):
        """
        Start the OSC server
        """
        try:
            host = EngineSettings.OSC.input_host
            port = EngineSettings.OSC.input_port
            
            logger.info(f"Starting OSC Server at {host}:{port}")
            
            self.server = ThreadingOSCUDPServer((host, port), self.dispatcher)
            
            server_thread = threading.Thread(
                target=self.server.serve_forever,
                daemon=True,
                name="OSCServer"
            )
            server_thread.start()
            
            logger.info(f"OSC Server started successfully at {host}:{port}")
            logger.info(f"Registered {len(self.message_handlers)} OSC addresses:")
            for addr in self.message_handlers.keys():
                logger.info(f"  - {addr}")
            logger.info("OSC Server is ready to receive messages")
            
            await asyncio.sleep(0.1)
            
        except Exception as e:
            logger.error(f"Error starting OSC server: {e}")
            raise
    
    async def stop(self):
        """
        Stop the OSC server
        """
        logger.info("Stopping OSC Server...")
        
        if self.server:
            self.server.shutdown()
            logger.info("OSC Server stopped.")
        
        if self.executor:
            self.executor.shutdown(wait=False)
            logger.info("OSC Executor stopped.")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get OSC handler statistics
        """
        with self._lock:
            return {
                "running": self.server is not None,
                "message_count": self.message_count,
                "error_count": self.error_count,
                "error_rate": self.error_count / max(1, self.message_count),
                "last_message_time": self.last_message_time,
                "handlers_count": len(self.message_handlers),
                "has_palette_handler": self.palette_handler is not None,
                "server_address": f"{EngineSettings.OSC.input_host}:{EngineSettings.OSC.input_port}" if self.server else None
            }
    
    def reset_stats(self):
        """
        Reset message statistics
        """
        with self._lock:
            self.message_count = 0
            self.error_count = 0
        logger.info("OSC handler statistics reset")