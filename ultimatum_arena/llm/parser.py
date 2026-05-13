"""Robust JSON extraction and response parsing for LLM outputs.

Models frequently wrap JSON in markdown code fences or add explanatory
text before/after the object.  extract_json() tries multiple strategies
before giving up.
"""

from __future__ import annotations

import json
import re

from ultimatum_arena.llm.errors import LLMParseError
from ultimatum_arena.schemas import ProposerAction, ProposerObservation, ResponderAction


# -----------------------------------------------------------------------
# JSON extraction
# -----------------------------------------------------------------------

def extract_json(text: str) -> dict:
    """Extract the first JSON object from *text*.

    Strategies tried in order:
    1. Direct ``json.loads`` of the stripped text.
    2. First ```json … ``` or ``` … ``` code block.
    3. First bare ``{…}`` span (greedy innermost match).

    Raises
    ------
    LLMParseError
        When no valid JSON object can be found.
    """
    stripped = text.strip()

    # Strategy 1: the whole response is already JSON
    try:
        obj = json.loads(stripped)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass

    # Strategy 2: JSON inside a markdown code fence
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", stripped, re.DOTALL)
    if fence:
        try:
            return json.loads(fence.group(1))
        except json.JSONDecodeError:
            pass

    # Strategy 3: locate the outermost { … } block
    start = stripped.find("{")
    if start != -1:
        depth, end = 0, -1
        for i, ch in enumerate(stripped[start:], start):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i
                    break
        if end != -1:
            try:
                return json.loads(stripped[start : end + 1])
            except json.JSONDecodeError:
                pass

    raise LLMParseError(
        f"No valid JSON object found in model response: {text!r}"
    )


# -----------------------------------------------------------------------
# Response parsers
# -----------------------------------------------------------------------

def parse_proposer_response(text: str, obs: ProposerObservation) -> ProposerAction:
    """Parse a model response into a :class:`ProposerAction`.

    Falls back to safe values derived from *obs* when individual fields
    are missing or out of range:
    - missing ``claimed_pie`` → ``obs.true_pie``
    - ``offer > claimed_pie`` → clamped to ``claimed_pie``
    - negative ``offer`` → 0

    Raises
    ------
    LLMParseError
        If the response cannot be parsed at all.
    """
    data = extract_json(text)

    try:
        claimed_pie = float(data["claimed_pie"])
    except (KeyError, TypeError, ValueError):
        claimed_pie = obs.true_pie

    if claimed_pie <= 0:
        claimed_pie = obs.true_pie

    try:
        offer = float(data["offer"])
    except (KeyError, TypeError, ValueError):
        offer = claimed_pie / 2

    offer = max(0.0, min(offer, claimed_pie))
    message = str(data.get("public_message", ""))

    return ProposerAction(
        claimed_pie=claimed_pie,
        offer=offer,
        public_message=message,
    )


def parse_responder_response(text: str) -> ResponderAction:
    """Parse a model response into a :class:`ResponderAction`.

    Accepts ``"accept"`` values of ``true``/``false`` (JSON booleans),
    or common string variants (``"yes"``/``"no"``/``"true"``/``"false"``).

    Raises
    ------
    LLMParseError
        If the response cannot be parsed at all.
    """
    data = extract_json(text)

    raw = data.get("accept")
    if isinstance(raw, bool):
        accept = raw
    elif isinstance(raw, str):
        accept = raw.strip().lower() in {"true", "yes", "1", "accept"}
    elif isinstance(raw, (int, float)):
        accept = bool(raw)
    else:
        # Key missing — treat as reject (safer default for a research game)
        accept = False

    return ResponderAction(accept=accept)
