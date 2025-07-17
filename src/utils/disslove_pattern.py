"""
Dissolve system implementation according to specifications
Manages dissolve patterns and crossfade transitions without dissolve_time parameter
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import json
import time

from src.utils.color_utils import ColorUtils
from src.models.types import DissolvePhase
from src.utils.logger import ComponentLogger

logger = ComponentLogger("Dissolve")


class DissolvePatternManager:
    """
    Manages dissolve patterns loaded from JSON files
    Handles pattern loading, selection, and retrieval without timing overrides
    """
    
    def __init__(self):
        self.patterns: Dict[int, List[List[int]]] = {}
        self.current_pattern_id: Optional[int] = None
    
    def load_patterns_from_json(self, file_path: str) -> bool:
        """
        Load dissolve patterns from JSON file
        
        Args:
            file_path: Path to JSON file containing dissolve patterns
            
        Returns:
            bool: True if patterns loaded successfully
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if 'dissolve_patterns' not in data:
                logger.error(f"Invalid JSON: missing 'dissolve_patterns' key in {file_path}")
                return False
            
            self.patterns.clear()
            
            for pattern_id_str, pattern_data in data['dissolve_patterns'].items():
                try:
                    pattern_id = int(pattern_id_str)
                    if isinstance(pattern_data, list):
                        self.patterns[pattern_id] = pattern_data
                        logger.debug(f"Loaded pattern {pattern_id} with {len(pattern_data)} transitions")
                except (ValueError, TypeError) as e:
                    logger.warning(f"Skipping invalid pattern {pattern_id_str}: {e}")
                    continue
            
            logger.info(f"Loaded {len(self.patterns)} dissolve patterns from {file_path}")
            return len(self.patterns) > 0
            
        except Exception as e:
            logger.error(f"Failed to load dissolve patterns from {file_path}: {e}")
            return False
    
    def get_pattern(self, pattern_id: int) -> Optional[List[List[int]]]:
        """
        Get pattern data by ID
        
        Args:
            pattern_id: Pattern identifier
            
        Returns:
            List of transitions or None if pattern not found
        """
        return self.patterns.get(pattern_id)
    
    def set_current_pattern(self, pattern_id: int) -> bool:
        """
        Set current active pattern
        
        Args:
            pattern_id: Pattern identifier to activate
            
        Returns:
            bool: True if pattern exists and was set
        """
        if pattern_id in self.patterns:
            self.current_pattern_id = pattern_id
            logger.info(f"Active dissolve pattern set to {pattern_id}")
            return True
        logger.warning(f"Pattern {pattern_id} not found in loaded patterns")
        return False
    
    def get_available_patterns(self) -> List[int]:
        """Get list of available pattern IDs"""
        return list(self.patterns.keys())
    
    def clear_current_pattern(self):
        """Clear current pattern selection (disable dissolve)"""
        self.current_pattern_id = None
        logger.info("Dissolve pattern cleared - transitions will be instant")
