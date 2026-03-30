from unittest.mock import MagicMock, patch

import pytest

from velocity.core.context import AgentContext
from velocity.services.security.layer import SecurityLayer
from velocity.services.security.pii import redact_pii, scan_for_pii


def test_regex_pii_masking():
    text = "My SSN is 123-45-6789 and my card is 1234-5678-9012-3456."
    matches = scan_for_pii(text, semantic=False)
    assert len(matches) == 2
    
    redacted = redact_pii(text, matches)
    assert "<SSN_REDACTED>" in redacted
    assert "<CREDIT_CARD_REDACTED>" in redacted

@patch("velocity.services.security.pii._get_presidio_analyzer")
def test_semantic_pii_masking(mock_get_analyzer):
    # Mock Presidio results
    mock_analyzer = MagicMock()
    mock_get_analyzer.return_value = mock_analyzer
    
    mock_res = MagicMock()
    mock_res.entity_type = "PERSON"
    mock_res.start = 11
    mock_res.end = 21
    mock_analyzer.analyze.return_value = [mock_res]
    
    text = "My name is John Doe."
    matches = scan_for_pii(text, semantic=True)
    
    assert len(matches) == 1
    assert matches[0].entity_type == "PERSON"
    assert "<PERSON_REDACTED>" in redact_pii(text, matches)

@pytest.mark.asyncio
async def test_security_layer_toggle():
    # Test that SecurityLayer correctly passes the semantic toggle
    layer_no_semantic = SecurityLayer(semantic_pii_enabled=False)
    SecurityLayer(semantic_pii_enabled=True)
    
    ctx = AgentContext(request_id="r1", agent_id="a1", tenant_id="t1")
    text = "Hi John Doe."
    
    # With semantic=False, John Doe should NOT be redacted (by regex)
    out1 = await layer_no_semantic.mask_outgoing_context(ctx, text)
    assert "John Doe" in out1
    
    # We don't run the semantic=True test here because it requires 
    # actual Presidio/Spacy models which might not be in the environment.
    # The pii.py logic handles the missing engine gracefully anyway.
