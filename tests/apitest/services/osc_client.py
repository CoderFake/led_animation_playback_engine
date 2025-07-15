"""
OSC Client Service - Strategy Pattern Implementation
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import socket
import json
import asyncio
from datetime import datetime
import re

from config.settings import settings
from dataclass.osc_models import OSCRequest, OSCResponse

class OSCClientStrategy(ABC):
    """Abstract OSC client strategy"""
    
    @abstractmethod
    async def send_message(self, request: OSCRequest) -> OSCResponse:
        """Send OSC message"""
        pass
    
    @abstractmethod
    async def check_connection(self) -> bool:
        """Check if connection is available"""
        pass

class UDPOSCClient(OSCClientStrategy):
    """UDP OSC client implementation"""
    
    def __init__(self, host: str = None, port: int = None):
        self.host = host or settings.config.osc_server.host
        self.port = port or settings.config.osc_server.port
        self.timeout = settings.config.osc_server.timeout
        
    async def send_message(self, request: OSCRequest) -> OSCResponse:
        """Send OSC message via UDP"""
        start_time = datetime.now()
        
        try:
            if not request.validate():
                return OSCResponse(
                    message_id=request.message_id,
                    status="error",
                    error="Invalid request parameters"
                )
            
           
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(self.timeout)
            
            osc_address = request.address
            osc_args = [param.value for param in request.parameters]
            
            print(f"[DEBUG] Sending OSC: {osc_address} {osc_args} to {self.host}:{self.port}")
            
            from pythonosc import osc_message_builder
            builder = osc_message_builder.OscMessageBuilder(osc_address)
            for arg in osc_args:
                builder.add_arg(arg)
            
            msg = builder.build()
            message_bytes = msg.dgram
            
            await asyncio.get_event_loop().run_in_executor(
                None, sock.sendto, message_bytes, (self.host, self.port)
            )
            
            print(f"[DEBUG] OSC message sent successfully")
            
            # Calculate response time
            response_time = (datetime.now() - start_time).total_seconds()
            
            return OSCResponse(
                message_id=request.message_id,
                status="success",
                data={"sent_at": start_time.isoformat(), "osc_address": osc_address, "osc_args": osc_args},
                response_time=response_time
            )
            
        except socket.timeout:
            print(f"[DEBUG] OSC timeout sending to {self.host}:{self.port}")
            return OSCResponse(
                message_id=request.message_id,
                status="error",
                error="Connection timeout"
            )
        except Exception as e:
            print(f"[DEBUG] OSC error: {e}")
            return OSCResponse(
                message_id=request.message_id,
                status="error",
                error=str(e)
            )
        finally:
            if 'sock' in locals():
                sock.close()
    
    async def check_connection(self) -> bool:
        """Check UDP connection availability"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(1.0)
            
            test_message = b"ping"
            await asyncio.get_event_loop().run_in_executor(
                None, sock.sendto, test_message, (self.host, self.port)
            )
            
            return True
        except Exception:
            return False
        finally:
            if 'sock' in locals():
                sock.close()

class MockOSCClient(OSCClientStrategy):
    """Mock OSC client for testing"""
    
    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail
        self.sent_messages: List[OSCRequest] = []
    
    async def send_message(self, request: OSCRequest) -> OSCResponse:
        """Mock send OSC message"""
        self.sent_messages.append(request)
        
        if self.should_fail:
            return OSCResponse(
                message_id=request.message_id,
                status="error",
                error="Mock failure"
            )
        
        return OSCResponse(
            message_id=request.message_id,
            status="success",
            data={"mock": True, "request": request.build()},
            response_time=0.001
        )
    
    async def check_connection(self) -> bool:
        """Mock connection check"""
        return not self.should_fail
    
    def get_sent_messages(self) -> List[OSCRequest]:
        """Get all sent messages"""
        return self.sent_messages.copy()
    
    def clear_messages(self):
        """Clear sent messages"""
        self.sent_messages.clear()

class OSCClientContext:
    """Context for OSC client strategies"""
    
    def __init__(self, strategy: OSCClientStrategy):
        self._strategy = strategy
    
    def set_strategy(self, strategy: OSCClientStrategy):
        """Change strategy"""
        self._strategy = strategy
    
    async def send_message(self, request: OSCRequest) -> OSCResponse:
        """Send message using current strategy"""
        return await self._strategy.send_message(request)
    
    async def check_connection(self) -> bool:
        """Check connection using current strategy"""
        return await self._strategy.check_connection()

class OSCMessageValidator:
    """Validator for OSC messages based on osc_handler.py"""
    
    @staticmethod
    def validate_palette_address(address: str) -> bool:
        """Validate palette address format: /palette/{palette_id}/{color_id}"""
        pattern = r"/palette/([A-E])/([0-5])"
        return bool(re.match(pattern, address))
    
    @staticmethod
    def validate_palette_rgb(rgb_values: List[int]) -> bool:
        """Validate RGB values for palette"""
        if len(rgb_values) != 3:
            return False
        
        return all(0 <= val <= 255 for val in rgb_values)
    
    @staticmethod
    def validate_palette_request(request: OSCRequest) -> Dict[str, Any]:
        """Validate palette request completely"""
        errors = []
        
        if not OSCMessageValidator.validate_palette_address(request.address):
            errors.append("Invalid palette address format. Expected: /palette/[A-E]/[0-5]")
        
        rgb_params = [p for p in request.parameters if p.name in ['r', 'g', 'b']]
        if len(rgb_params) != 3:
            errors.append("Missing RGB parameters")
        else:
            rgb_values = [p.value for p in rgb_params]
            if not OSCMessageValidator.validate_palette_rgb(rgb_values):
                errors.append("Invalid RGB values. Must be integers 0-255")
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors
        } 