"""
OSC Data Models - Builder Pattern Implementation
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from enum import Enum
import json
import uuid
from datetime import datetime

class OSCMessageType(Enum):
    """OSC message types"""
    LED_CONTROL = "led_control"
    BRIGHTNESS = "brightness"
    COLOR = "color"
    PATTERN = "pattern"
    STATUS = "status"

class OSCDataType(Enum):
    """OSC data types"""
    INT = "int"
    FLOAT = "float"
    STRING = "string"
    BOOL = "bool"
    BLOB = "blob"

@dataclass
class OSCParameter:
    """OSC parameter data model"""
    name: str
    value: Any
    data_type: OSCDataType
    description: Optional[str] = None
    
    def validate(self) -> bool:
        """Validate parameter value against data type"""
        if self.data_type == OSCDataType.INT:
            return isinstance(self.value, int)
        elif self.data_type == OSCDataType.FLOAT:
            return isinstance(self.value, (int, float))
        elif self.data_type == OSCDataType.STRING:
            return isinstance(self.value, str)
        elif self.data_type == OSCDataType.BOOL:
            return isinstance(self.value, bool)
        return True

@dataclass
class OSCRequest:
    """OSC Request Builder Pattern"""
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    address: str = ""
    message_type: OSCMessageType = OSCMessageType.LED_CONTROL
    parameters: List[OSCParameter] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_parameter(self, name: str, value: Any, data_type: OSCDataType, description: str = None) -> 'OSCRequest':
        """Builder method to add parameter"""
        param = OSCParameter(name, value, data_type, description)
        self.parameters.append(param)
        return self
    
    def set_address(self, address: str) -> 'OSCRequest':
        """Builder method to set address"""
        self.address = address
        return self
    
    def set_message_type(self, message_type: OSCMessageType) -> 'OSCRequest':
        """Builder method to set message type"""
        self.message_type = message_type
        return self
    
    def add_metadata(self, key: str, value: Any) -> 'OSCRequest':
        """Builder method to add metadata"""
        self.metadata[key] = value
        return self
    
    def build(self) -> Dict[str, Any]:
        """Build final request dictionary"""
        return {
            "message_id": self.message_id,
            "address": self.address,
            "message_type": self.message_type.value,
            "parameters": [
                {
                    "name": param.name,
                    "value": param.value,
                    "data_type": param.data_type.value,
                    "description": param.description
                }
                for param in self.parameters
            ],
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }
    
    def validate(self) -> bool:
        """Validate all parameters"""
        return all(param.validate() for param in self.parameters)

@dataclass
class OSCResponse:
    """OSC Response data model"""
    message_id: str
    status: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    response_time: Optional[float] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OSCResponse':
        """Create OSCResponse from dictionary"""
        return cls(
            message_id=data.get("message_id", ""),
            status=data.get("status", ""),
            data=data.get("data"),
            error=data.get("error"),
            timestamp=datetime.fromisoformat(data.get("timestamp", datetime.now().isoformat())),
            response_time=data.get("response_time")
        )
    
    def is_success(self) -> bool:
        """Check if response is successful"""
        return self.status == "success" and self.error is None

@dataclass
class OSCTestCase:
    """OSC Test case data model"""
    name: str
    description: str
    request: OSCRequest
    expected_response: Optional[Dict[str, Any]] = None
    tags: List[str] = field(default_factory=list)
    timeout: float = 5.0
    
    def add_tag(self, tag: str) -> 'OSCTestCase':
        """Add tag to test case"""
        self.tags.append(tag)
        return self 