"""Field / source labels from translate/rules/<lang>.json (single source of truth)."""

from __future__ import annotations

from translate.lib.config import load_lang_rules

# CN source bullet uses fullwidth colon; translations use ASCII.
_CN_COLON = "："
_TR_COLON = ":"

# Position of the plain-terms field (说人话 / In plain terms / Простыми словами)
# inside field_labels(lang).
PLAIN_FIELD_INDEX = 1


def field_labels(lang: str, root: str | None = None) -> list[str]:
    """Five item-field names for `lang` (成本… / Cost… / …)."""
    pack = load_lang_rules(lang if lang != "cn" else "cn", root=root)
    labels = pack.get("labels") or {}
    if lang not in labels:
        raise KeyError(f"rules/{lang if lang != 'cn' else 'cn'}.json missing labels[{lang!r}]")
    return list(labels[lang])


def source_label(lang: str, root: str | None = None) -> str:
    """Bare source-field word: 来源 / Sources / Источники / Fuentes."""
    pack = load_lang_rules("cn" if lang == "cn" else lang, root=root)
    label = pack.get("source_label")
    if not label:
        raise KeyError(f"rules pack for {lang!r} missing source_label")
    return label


def evidence_grade_label(lang: str, root: str | None = None) -> str:
    """Bare evidence-grade field word for assembly rewrites."""
    pack = load_lang_rules(lang, root=root)
    label = pack.get("evidence_grade_label")
    if not label:
        # Fall back to 4th field label (证据等级 / Evidence grade / …)
        fields = field_labels(lang, root=root)
        return fields[3]
    return label


def source_bullet(lang: str, root: str | None = None) -> str:
    """Full source line prefix including dash and colon: '- Sources:' / '- 来源：'."""
    word = source_label(lang, root=root)
    colon = _CN_COLON if lang == "cn" else _TR_COLON
    return f"- {word}{colon}"


def banned_calques(lang: str, root: str | None = None) -> list[str]:
    """Banned calque stems for `lang` (empty list if none)."""
    if lang == "cn":
        return []
    pack = load_lang_rules(lang, root=root)
    return list(pack.get("banned_calques") or [])
