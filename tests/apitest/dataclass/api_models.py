"""
API Request/Response Models - Pydantic Models
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

class LoadJsonRequest(BaseModel):
    """Load scene from JSON file"""
    file_path: str

class LoadDissolveJsonRequest(BaseModel):
    """Load dissolve pattern from JSON file"""
    file_path: str

class ChangeSceneRequest(BaseModel):
    """Change scene request"""
    scene_id: int

class ChangeEffectRequest(BaseModel):
    """Change effect request"""
    effect_id: int

class ChangePaletteRequest(BaseModel):
    """Change palette request"""
    palette_id: int

class PaletteColorRequest(BaseModel):
    """Update palette color request"""
    r: int
    g: int
    b: int

class SetDissolvePatternRequest(BaseModel):
    """Set dissolve pattern request"""
    pattern_id: int

class SpeedPercentRequest(BaseModel):
    """Set speed percent request - expanded range 0-1023%"""
    percent: int

class MasterBrightnessRequest(BaseModel):
    """Set master brightness request"""
    brightness: int

class ChangePatternRequest(BaseModel):
    """Change pattern request - Execute cached changes"""
    pass

class PauseRequest(BaseModel):
    """Pause animation request - no parameters needed"""
    pass

class ResumeRequest(BaseModel):
    """Resume animation request - no parameters needed"""
    pass

class OSCApiResponse(BaseModel):
    """OSC API response"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat()) 