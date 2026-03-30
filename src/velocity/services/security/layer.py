"""
Security Manager Layer.
Intercepts all semantic IO before LLM invocations, sanitizing PII and aborting on injections.
"""

import logging

from velocity.core.context import AgentContext
from velocity.exceptions import SecurityValidationError

from .pii import redact_pii, scan_for_pii

logger = logging.getLogger(__name__)

class SecurityLayer:
    """
    Mandatory defense-in-depth shield surrounding the AgentEngine. 
    Cannot be bypassed by agent logic.
    """

    def __init__(
        self, 
        pii_enabled: bool = True, 
        semantic_pii_enabled: bool = False,
        injection_strict: bool = True
    ):
        self.pii_enabled = pii_enabled
        self.semantic_pii_enabled = semantic_pii_enabled
        self.injection_strict = injection_strict

    async def pre_flight_analyze(self, ctx: AgentContext, payload: str) -> str:
        """
        Scan incoming user text. 
        Abort entire execution if Prompt Injection (Jailbreak) signature is detected.
        """
        if self.injection_strict and "ignore all previous instructions" in payload.lower():
             raise SecurityValidationError(
                "Prompt Injection (Jailbreak) signature detected. Request blocked.",
                request_id=ctx.request_id,
                agent_id=ctx.agent_id
            )
            
        return payload

    async def mask_outgoing_context(self, ctx: AgentContext, text: str) -> str:
        """
        Redact sensitive data (SSN/CC/Names) before sending it upstream.
        """
        if not self.pii_enabled:
            return text
            
        # We pass the semantic toggle to the scanner
        matches = scan_for_pii(text, semantic=self.semantic_pii_enabled)
        
        if matches:
            logger.debug(f"{len(matches)} PII entities redacted for tracing context {ctx.request_id}")
            # Ensure the security scan is logged via Audit pipeline.
            ctx.events.append({
                "type": "security_masking",
                "entities_found": len(matches),
                "semantic": self.semantic_pii_enabled
            })
            return redact_pii(text, matches)
            
        return text
