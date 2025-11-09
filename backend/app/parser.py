"""Hybrid command parser - rules-first with optional LLM fallback"""
import re
from typing import Dict, Any, Tuple, Optional
from app.models import ParseResult
from app.config import settings

# Rule-based patterns
RULES = [
    # Time queries
    (r'^(what time is it|current time|time|what\'s the time)\??$', 
     'system.time', {}, 1.0),
    
    # File write
    (r'^write file ([\w\.\-]+):\s*(.+)$', 
     'files.write', lambda m: {'filename': m.group(1), 'content': m.group(2)}, 0.95),
    
    # File read
    (r'^read file ([\w\.\-]+)$', 
     'files.read', lambda m: {'filename': m.group(1)}, 0.95),
    
    # File delete
    (r'^delete file ([\w\.\-]+)$', 
     'files.delete', lambda m: {'filename': m.group(1)}, 0.95),
    
    # File copy
    (r'^copy file ([\w\.\-]+) to ([\w\.\-]+)$', 
     'files.copy', lambda m: {'source': m.group(1), 'dest': m.group(2)}, 0.95),
    
    # File move
    (r'^move file ([\w\.\-]+) to ([\w\.\-]+)$', 
     'files.move', lambda m: {'source': m.group(1), 'dest': m.group(2)}, 0.95),
    
    # List files
    (r'^(list files|ls|dir|show files)(\s+in\s+([\w\.\-/]+))?$', 
     'files.list', lambda m: {'path': m.group(3) if m.group(3) else ''}, 0.90),
    
    # Open application
    (r'^open (chrome|firefox|safari|edge|browser|notepad|calculator|terminal)$', 
     'apps.open', lambda m: {'app': m.group(1)}, 0.90),
]

def parse_with_rules(utterance: str) -> Tuple[Optional[str], Dict[str, Any], float]:
    """Parse utterance using rule-based patterns"""
    text = utterance.lower().strip()
    
    for pattern, intent, args_fn, confidence in RULES:
        match = re.match(pattern, text)
        if match:
            # Extract args
            if callable(args_fn):
                args = args_fn(match)
            else:
                args = args_fn
            
            return intent, args, confidence
    
    # No match found
    return None, {}, 0.0

def parse_with_llm(utterance: str, context: Dict[str, Any]) -> ParseResult:
    """Parse utterance using LLM (fallback)"""
    # TODO: Implement LLM-based parsing when API key is available
    # For now, return low confidence result
    return ParseResult(
        intent="unknown",
        args={"utterance": utterance},
        confidence=0.3,
        source="llm"
    )

def parse(utterance: str, context: Optional[Dict[str, Any]] = None) -> ParseResult:
    """Main parser interface - hybrid approach"""
    context = context or {}
    
    # Try rules first
    intent, args, confidence = parse_with_rules(utterance)
    
    if intent and confidence >= settings.confidence_high:
        # High confidence rule match
        return ParseResult(
            intent=intent,
            args=args,
            confidence=confidence,
            source="rules"
        )
    
    # Check parser mode
    if settings.parser_mode == "rules":
        # Rules only mode
        if intent:
            return ParseResult(
                intent=intent,
                args=args,
                confidence=confidence,
                source="rules"
            )
        else:
            return ParseResult(
                intent="unknown",
                args={"utterance": utterance},
                confidence=0.0,
                source="rules"
            )
    
    elif settings.parser_mode == "hybrid":
        # Hybrid mode: use LLM fallback if confidence is low
        if intent and confidence >= settings.confidence_low:
            # Medium confidence, use rule result
            return ParseResult(
                intent=intent,
                args=args,
                confidence=confidence,
                source="rules"
            )
        else:
            # Low confidence or no match, try LLM
            if settings.llm_api_key:
                return parse_with_llm(utterance, context)
            else:
                # No LLM available, return best rule match or unknown
                if intent:
                    return ParseResult(
                        intent=intent,
                        args=args,
                        confidence=confidence,
                        source="rules"
                    )
                else:
                    return ParseResult(
                        intent="unknown",
                        args={"utterance": utterance},
                        confidence=0.0,
                        source="rules"
                    )
    
    else:  # llm mode
        # Always use LLM
        if settings.llm_api_key:
            return parse_with_llm(utterance, context)
        else:
            # Fall back to rules if no LLM available
            if intent:
                return ParseResult(
                    intent=intent,
                    args=args,
                    confidence=confidence,
                    source="rules"
                )
            else:
                return ParseResult(
                    intent="unknown",
                    args={"utterance": utterance},
                    confidence=0.0,
                    source="rules"
                )