"""Locked Laya questions for RU style labels (данные/эти, при, согласно).

Maps style_check marker labels → Jev-compatible question dicts. Answers are
interpreted as ``bug`` | ``ok`` | ``unclear`` by triage.
"""

from __future__ import annotations

from typing import Any

# style_check labels that Laya may triage (RU only for now).
TRIAGE_LABELS: frozenset[str] = frozenset(
    {
        "этих-вместо-данных",
        "согласно-творительный",
        "при-родительный-после-рамок",
    }
)

_CHOICE_BUG_OK_UNCLEAR: dict[str, Any] = {
    "type": "choice",
    "criteria": {
        "bug": "True style error / calque — should be fixed",
        "ok": "False positive — wording is fine",
        "unclear": "Cannot decide from this span alone",
    },
}


def questions_for_label(label: str) -> dict[str, Any] | None:
    """Return ``{qid: question}`` for a triageable label, else None."""
    if label == "этих-вместо-данных":
        return {
            "verdict": {
                **_CHOICE_BUG_OK_UNCLEAR,
                "instructions": (
                    "Russian style audit flagged this span as likely rewriting the noun "
                    "«данные» (data) into a demonstrative «эти/этих». "
                    "Is that a real error (bug), acceptable demonstrative use (ok), "
                    "or unclear?"
                ),
            }
        }
    if label == "согласно-творительный":
        return {
            "verdict": {
                **_CHOICE_BUG_OK_UNCLEAR,
                "instructions": (
                    "Russian «согласно» requires the dative (закону, требованиям), "
                    "not the instrumental (законом, требованиями). "
                    "Is the flagged span a real case error (bug), fine (ok), or unclear?"
                ),
            }
        }
    if label == "при-родительный-после-рамок":
        return {
            "verdict": {
                **_CHOICE_BUG_OK_UNCLEAR,
                "instructions": (
                    "Style audit flagged «при» + genitive as a likely calque after "
                    "dropping «в рамках». Is this a real awkward/calqued «при» (bug), "
                    "natural Russian (ok), or unclear?"
                ),
            }
        }
    return None


def interpret_answer(payload: dict[str, Any] | None) -> str:
    """Map a /v1/systemone response to bug|ok|unclear (default unclear)."""
    if not payload:
        return "unclear"
    answers = payload.get("answers") or {}
    block = answers.get("verdict") or {}
    if isinstance(block, dict):
        ans = block.get("answer")
        if ans in ("bug", "ok", "unclear"):
            return str(ans)
        # noul-shaped fallback
        if block.get("type") == "noul" and "answer" in block:
            return "bug" if block["answer"] else "ok"
    return "unclear"
