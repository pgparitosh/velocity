"""
Personally Identifiable Information (PII) auditing and masking.
Mandatory compliance layer ensuring financial or health data does not leak 
to third-party LLM providers unconditionally.
"""

import logging
import re
from dataclasses import dataclass
from typing import Any

try:
    from presidio_analyzer import AnalyzerEngine
    from presidio_anonymizer import AnonymizerEngine
    from presidio_anonymizer.entities import OperatorConfig
except ImportError:
    AnalyzerEngine: Any = None  # type: ignore[no-redef]
    AnonymizerEngine: Any = None  # type: ignore[no-redef]

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class PiiMatch:
    entity_type: str
    start: int
    end: int
    matched_text: str


# Deterministic high-confidence patterns (e.g. SSN, Credit Cards)
PII_PATTERNS = {
    # Basic US SSN format (AAA-GG-SSSS)
    "SSN": re.compile(r"\b(?!(000|666|9))\d{3}-(?!00)\d{2}-(?!0000)\d{4}\b"),
    # Credit Card baseline
    "CREDIT_CARD": re.compile(r"\b(?:\d[ -]*?){13,16}\b")
}

# Lazy-loaded Presidio engines
_ANALYZER: AnalyzerEngine | None = None
_ANONYMIZER: AnonymizerEngine | None = None

def _get_presidio_analyzer() -> AnalyzerEngine | None:
    global _ANALYZER
    if _ANALYZER is None and AnalyzerEngine:
        try:
            _ANALYZER = AnalyzerEngine()
        except Exception as e:
            logger.warning(f"Failed to initialize Presidio Analyzer: {e}")
    return _ANALYZER

def scan_for_pii(text: str, semantic: bool = False) -> list[PiiMatch]:
    """
    Identifies sensitive data blocks within arbitrary agent text.
    
    Args:
        text: Input string to scan.
        semantic: If True, uses NLP-based detection (Presidio) for Names/Locations.
    """
    matches = []
    
    # 1. Faster Regex-based pass (High confidence)
    for entity_type, pattern in PII_PATTERNS.items():
        for match in pattern.finditer(text):
            matches.append(PiiMatch(
                entity_type=entity_type,
                start=match.start(),
                end=match.end(),
                matched_text=match.group(0)
            ))
            
    # 2. Semantic NLP-based pass (Presidio)
    if semantic:
        analyzer = _get_presidio_analyzer()
        if analyzer:
            # We map specific Presidio entities to our PiiMatch structure
            results = analyzer.analyze(text=text, entities=["PERSON", "LOCATION", "PHONE_NUMBER", "EMAIL_ADDRESS"], language='en')
            for res in results:
                # Deduplicate if regex already caught it (e.g. phone numbers)
                is_duplicate = any(m.start == res.start and m.end == res.end for m in matches)
                if not is_duplicate:
                    matches.append(PiiMatch(
                        entity_type=res.entity_type,
                        start=res.start,
                        end=res.end,
                        matched_text=text[res.start:res.end]
                    ))
                    
    return matches

def redact_pii(text: str, matches: list[PiiMatch]) -> str:
    """
    Replaces matched spans with `<REDACTED_TYPE>` tokens securely.
    """
    # Sort matches by start index descending to avoid offset shifting 
    sorted_matches = sorted(matches, key=lambda x: x.start, reverse=True)
    
    redacted_text = text
    for match in sorted_matches:
        replacement = f"<{match.entity_type}_REDACTED>"
        redacted_text = redacted_text[:match.start] + replacement + redacted_text[match.end:]
        
    return redacted_text
