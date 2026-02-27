"""
Vision Router for Agent Zero
Detects vision-capable tasks and routes to appropriate vision models.
Integrates with NvidiaRouter for multi-model vision support.
"""
from __future__ import annotations
import re
from dataclasses import dataclass


@dataclass
class VisionRoutingResult:
    needs_vision: bool
    model: str
    reason: str


# Patterns that indicate a vision/image task
VISION_PATTERNS = [
    r'\b(image|picture|photo|screenshot|diagram|chart|graph|figure|illustration)\b',
    r'\b(look at|see|view|analyze|describe|examine)\s+(the\s+)?(image|picture|photo|screenshot)',
    r'\b(vision|visual|optical|OCR|read.*text.*image)\b',
    r'\b(base64|data:image|\.png|\.jpg|\.jpeg|\.gif|\.webp|\.svg|\.bmp)\b',
    r'\b(what.*(in|on)\s+(this|the)\s+(image|picture|photo|screen))\b',
]

# Known vision-capable models (from NVIDIA catalog and common providers)
VISION_MODELS = [
    "nvidia/llama-3.2-11b-vision-instruct",
    "nvidia/llama-3.2-90b-vision-instruct",
    "moonshotai/kimi-k2.5",
]


def detect_vision_task(message: str) -> bool:
    """Return True if the message likely requires vision capabilities."""
    text = message.lower()
    for pattern in VISION_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def route_vision(message: str, current_model: str = "", has_vision: bool = False) -> VisionRoutingResult:
    """
    Decide whether to route to a vision model.
    Returns the recommended model and reason.
    """
    needs = detect_vision_task(message)

    if not needs:
        return VisionRoutingResult(needs_vision=False, model=current_model, reason="no vision indicators")

    # If current model already supports vision, stay with it
    if has_vision:
        return VisionRoutingResult(needs_vision=True, model=current_model, reason="current model has vision")

    # Try NVIDIA vision models via router
    try:
        from python.helpers.nvidia_router import NvidiaRouter, NvidiaRole
        router = NvidiaRouter.instance()
        browser_model = router.get_model(NvidiaRole.BROWSER)
        browser_key = router.get_api_key(NvidiaRole.BROWSER)
        if browser_model and browser_key:
            return VisionRoutingResult(
                needs_vision=True,
                model=browser_model,
                reason=f"routed to NVIDIA browser model ({browser_model})",
            )
    except Exception:
        pass

    # Fallback to first known vision model
    return VisionRoutingResult(
        needs_vision=True,
        model=VISION_MODELS[0],
        reason=f"fallback to {VISION_MODELS[0]}",
    )
