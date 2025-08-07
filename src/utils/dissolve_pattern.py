"""
Dissolve pattern management for LED Animation Engine
Handles loading and managing dissolve patterns from JSON files
"""

from typing import List, Dict, Any, Optional
import json
from pathlib import Path

from src.utils.logger import ComponentLogger

logger = ComponentLogger("DissolvePattern")


class DissolvePatternManager:
    """
    Manages dissolve patterns loaded from JSON files
    Handles pattern loading, selection, and retrieval for dual pattern transitions
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
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                logger.error(f"Dissolve pattern file not found: {file_path}")
                return False
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if 'dissolve_patterns' not in data:
                logger.error(f"Invalid JSON: missing 'dissolve_patterns' key in {file_path}")
                return False
            
            self.patterns.clear()
            patterns_loaded = 0
            
            for pattern_id_str, pattern_data in data['dissolve_patterns'].items():
                try:
                    pattern_id = int(pattern_id_str)
                    
                    if not isinstance(pattern_data, list):
                        logger.warning(f"Pattern {pattern_id} data is not a list, skipping")
                        continue
                    
                    valid_transitions = []
                    for i, transition in enumerate(pattern_data):
                        if self._validate_transition_data(transition):
                            valid_transitions.append(transition)
                        else:
                            logger.warning(f"Invalid transition {i} in pattern {pattern_id}: {transition}")
                    
                    if valid_transitions:
                        self.patterns[pattern_id] = valid_transitions
                        patterns_loaded += 1
                    else:
                        logger.warning(f"Pattern {pattern_id} has no valid transitions")
                        
                except (ValueError, TypeError) as e:
                    logger.warning(f"Skipping invalid pattern {pattern_id_str}: {e}")
                    continue
            
            logger.info(f"Loaded {patterns_loaded} dissolve patterns from {file_path}")
            
            if patterns_loaded > 0:
                available_ids = list(self.patterns.keys())
                logger.info(f"Available pattern IDs: {sorted(available_ids)}")
                return True
            else:
                logger.error("No valid patterns found in file")
                return False
            
        except Exception as e:
            logger.error(f"Failed to load dissolve patterns from {file_path}: {e}")
            return False
    
    def _validate_transition_data(self, transition) -> bool:
        """
        Validate transition data format and values
        Expected format: [delay_ms, duration_ms, start_led, end_led]
        """
        if not isinstance(transition, (list, tuple)) or len(transition) != 4:
            return False
        
        try:
            delay_ms, duration_ms, start_led, end_led = transition
            
            if not all(isinstance(x, (int, float)) for x in [delay_ms, duration_ms]):
                return False
            
            if not all(isinstance(x, int) for x in [start_led, end_led]):
                return False
            
            if delay_ms < 0 or duration_ms <= 0:
                return False
            
            if start_led < 0 or end_led < 0 or start_led > end_led:
                return False
            
            return True
            
        except Exception:
            return False
    
    def get_pattern(self, pattern_id: int) -> Optional[List[List[int]]]:
        """
        Get pattern data by ID
        
        Args:
            pattern_id: Pattern identifier
            
        Returns:
            List of transitions or None if pattern not found
        """
        pattern = self.patterns.get(pattern_id)
        if not pattern:
            logger.warning(f"Pattern {pattern_id} not found")
        return pattern
    
    def set_current_pattern(self, pattern_id: int) -> bool:
        """
        Set current active pattern
        
        Args:
            pattern_id: Pattern identifier to activate
            
        Returns:
            bool: True if pattern exists and was set
        """
        if pattern_id in self.patterns:
            old_pattern = self.current_pattern_id
            self.current_pattern_id = pattern_id
            logger.info(f"Active dissolve pattern changed: {old_pattern} → {pattern_id}")
            return True
        else:
            available = list(self.patterns.keys())
            logger.warning(f"Pattern {pattern_id} not found. Available patterns: {available}")
            return False
    
    def get_available_patterns(self) -> List[int]:
        """Get list of available pattern IDs"""
        return sorted(list(self.patterns.keys()))
    