"""
Enhanced API Request/Response Models with /change_pattern support
File: tests/apitest/dataclass/api_models.py

Changes:
- Added ChangePatternRequest model
- Enhanced request validation
- Added pattern combination support
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime

class LoadJsonRequest(BaseModel):
    """Load scene from JSON file"""
    file_path: str

class LoadDissolveJsonRequest(BaseModel):
    """Load dissolve pattern from JSON file"""
    file_path: str

class ChangeSceneRequest(BaseModel):
    """Change scene request (parameter only, no animation trigger)"""
    scene_id: int

class ChangeEffectRequest(BaseModel):
    """Change effect request (parameter only, no animation trigger)"""
    effect_id: int

class ChangePaletteRequest(BaseModel):
    """Change palette request (parameter only, no animation trigger)"""
    palette_id: int

class ChangePatternRequest(BaseModel):
    """
    Change pattern request (no arguments - uses current scene manager state)
    
    This endpoint uses the current state that has been set by:
    - /change_scene (sets scene parameter)
    - /change_effect (sets effect parameter) 
    - /change_palette (sets palette parameter)
    
    If no state is set, uses defaults from current scene.
    """
    pass 

class PaletteColorRequest(BaseModel):
    """Update palette color request"""
    r: int = Field(..., ge=0, le=255, description="Red component (0-255)")
    g: int = Field(..., ge=0, le=255, description="Green component (0-255)")
    b: int = Field(..., ge=0, le=255, description="Blue component (0-255)")

class SetDissolvePatternRequest(BaseModel):
    """Set dissolve pattern request"""
    pattern_id: int = Field(..., ge=0, description="Dissolve pattern ID (0-origin)")

class DissolveTimeRequest(BaseModel):
    """Set dissolve time request"""
    time_ms: int = Field(..., ge=0, description="Dissolve time in milliseconds")

class SpeedPercentRequest(BaseModel):
    """Set speed percent request - expanded range 0-1023%"""
    percent: int = Field(..., ge=0, le=1023, description="Speed percentage (0-1023%)")

class MasterBrightnessRequest(BaseModel):
    """Set master brightness request"""
    brightness: int = Field(..., ge=0, le=255, description="Master brightness (0-255)")

class OSCApiResponse(BaseModel):
    """OSC API response with enhanced status tracking"""
    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Human-readable status message")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Response timestamp")
    action_type: Optional[str] = Field(None, description="Type of action performed")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "Pattern changed successfully",
                "data": {
                    "pattern": "scene=1, effect=2, palette=0",
                    "dissolve_triggered": True,
                    "animation_started": False
                },
                "timestamp": "2025-01-14T10:30:00.123456",
                "action_type": "pattern_change"
            }
        }

class PatternStatusResponse(BaseModel):
    """Pattern status response for /change_pattern"""
    success: bool
  
    class Config:
        schema_extra = {
            "example": {
                "success": True
            }
        }