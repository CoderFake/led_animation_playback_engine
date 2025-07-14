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
        logger.debug(f"Added OSC handler for: {address}")
    
    def add_palette_handler(self, handler: Callable):
        """
        Add a handler for palette color updates (supports both old and new formats)
        """
        self.palette_handler = handler
        
        palette_pattern_old = "/palette/*/*"
        self.dispatcher.map(palette_pattern_old, self._handle_palette_message)
        logger.debug("Added palette color handler (supports both string and int IDs)")
    
    def _create_wrapper(self, address: str, handler: Callable):
        """
        Create a wrapper function for a handler with proper logging
        """
        def wrapper(osc_address: str, *args):
            try:
                with self._lock:
                    self.message_count += 1
                    self.last_message_time = time.time()
                
                osc_logger.log_message(osc_address, args)
                
                future = self.executor.submit(self._safe_handler_call, handler, osc_address, *args)
                
            except Exception as e:
                with self._lock:
                    self.error_count += 1
                osc_logger.log_error(f"Error wrapping OSC message {osc_address}: {e}")
        
        return wrapper
    
    def _safe_handler_call(self, handler: Callable, osc_address: str, *args):
        """
        Call a handler safely with error handling
        """
        try:
            start_time = time.time()
            
            handler(osc_address, *args)
            
            process_time = time.time() - start_time
            if process_time > 0.1: 
                logger.warning(f"OSC handler {osc_address} took {process_time:.3f}s to process")
                
        except Exception as e:
            with self._lock:
                self.error_count += 1
            osc_logger.log_error(f"Error in OSC handler {osc_address}: {e}")
    
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
            
            osc_logger.log_message(address, args)
            
            pattern_old = r"/palette/([A-E])/([0-5])"
            pattern_new = r"/palette/([0-4])/([0-5])"
            
            match_old = re.match(pattern_old, address)
            match_new = re.match(pattern_new, address)
            
            palette_id = None
            color_id = None
            
            if match_old:
                palette_letter = match_old.group(1)
                palette_id = ord(palette_letter.upper()) - ord('A')  
                color_id = int(match_old.group(2))
                osc_logger.log_message(f"Converted palette {palette_letter} to {palette_id}", ())
            elif match_new:
                palette_id = int(match_new.group(1))
                color_id = int(match_new.group(2))
            else:
                osc_logger.log_error(f"Invalid palette address format: {address}")
                return
            
            if len(args) < 3:
                osc_logger.log_error(f"Insufficient RGB values for {address}: {args}")
                return
            
            rgb = [int(args[0]), int(args[1]), int(args[2])]
            
            for i in range(3):
                rgb[i] = max(0, min(255, rgb[i]))
            
            if self.palette_handler:
                future = self.executor.submit(
                    self._safe_palette_handler_call, 
                    self.palette_handler, address, palette_id, color_id, rgb
                )
                
        except Exception as e:
            with self._lock:
                self.error_count += 1
            osc_logger.log_error(f"Error handling palette message {address}: {e}")
    
    def _safe_palette_handler_call(self, handler: Callable, address: str, palette_id: int, color_id: int, rgb: List[int]):
        """
        Call palette handler safely with zero-origin int palette_id
        """
        try:
            handler(address, palette_id, color_id, rgb)
        except Exception as e:
            osc_logger.log_error(f"Error in palette handler {address}: {e}")
    
    def _handle_unknown_message(self, address: str, *args):
        """
        Handle unknown OSC messages
        """
        logger.warning(f"Unknown OSC message: {address} {args}")
    
    async def start(self):
        """
        Start the OSC server
        """
        try:
            host = EngineSettings.OSC.input_host
            port = EngineSettings.OSC.input_port
            
            self.server = ThreadingOSCUDPServer((host, port), self.dispatcher)
            
            server_thread = threading.Thread(
                target=self.server.serve_forever,
                daemon=True,
                name="OSCServer"
            )
            server_thread.start()
            
            logger.info(f"OSC Server started at {host}:{port}")
            logger.info(f"Registered OSC addresses: {list(self.message_handlers.keys())}")
            logger.info("Supports both old (A-E) and new (0-4) palette ID formats")
            
            await asyncio.sleep(0.1)
            
        except Exception as e:
            logger.error(f"Error starting OSC server: {e}")
            raise
    
    async def stop(self):
        """
        Stop the OSC server
        """
        if self.server:
            self.server.shutdown()
            logger.info("OSC Server stopped.")
        
        if self.executor:
            self.executor.shutdown(wait=False)
            logger.info("OSC Executor stopped.")
    
    def get_registered_addresses(self) -> List[str]:
        """
        Get the list of registered addresses
        """
        addresses = list(self.message_handlers.keys())
        addresses.append("/palette/*/*")
        return addresses
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get OSC statistics
        """
        with self._lock:
            return {
                "message_count": self.message_count,
                "error_count": self.error_count,
                "last_message_time": self.last_message_time,
                "registered_addresses": len(self.message_handlers),
                "executor_active": self.executor and not self.executor._shutdown,
                "server_running": self.server is not None,
                "palette_format_support": "both_old_and_new"
            }