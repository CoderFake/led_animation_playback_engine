"""
API Request/Response Models - Pydantic Models
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

class LoadJsonRequest(BaseModel):
    """Load scene from JSON file"""
    file_path: str = Field(..., description="Path to JSON file")

class LoadDissolveJsonRequest(BaseModel):
    """Load dissolve pattern from JSON file"""
    file_path: str = Field(..., description="Path to dissolve JSON file")

class ChangeSceneRequest(BaseModel):
    """Change scene request"""
    scene_id: int = Field(..., ge=0, description="Scene ID")

class ChangeEffectRequest(BaseModel):
    """Change effect request"""
    effect_id: int = Field(..., ge=0, description="Effect ID")

class ChangePaletteRequest(BaseModel):
    """Change palette request"""
    palette_id: int = Field(..., ge=0, le=5, description="Palette ID (0-5)")

class PaletteColorRequest(BaseModel):
    """Update palette color request"""
    r: int = Field(..., ge=0, le=255, description="Red component (0-255)")
    g: int = Field(..., ge=0, le=255, description="Green component (0-255)")
    b: int = Field(..., ge=0, le=255, description="Blue component (0-255)")

class DissolveTimeRequest(BaseModel):
    """Set dissolve time request"""
    time_ms: int = Field(..., ge=0, description="Dissolve time in milliseconds")

class SpeedPercentRequest(BaseModel):
    """Set speed percent request"""
    percent: int = Field(..., ge=0, le=200, description="Speed percentage (0-200%)")

class MasterBrightnessRequest(BaseModel):
    """Set master brightness request"""
    brightness: int = Field(..., ge=0, le=255, description="Master brightness (0-255)")

class OSCApiResponse(BaseModel):
    """OSC API response"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat()) 