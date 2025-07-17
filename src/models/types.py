from enum import Enum

class TransitionPhase(Enum):
    """Pattern transition phases"""
    FADE_OUT = "fade_out"
    WAITING = "waiting" 
    FADE_IN = "fade_in"
    COMPLETED = "completed"


class DissolvePhase(Enum):
    """Dissolve transition phases"""
    WAITING = "waiting"
    CROSSFADING = "crossfading"  
    COMPLETED = "completed"