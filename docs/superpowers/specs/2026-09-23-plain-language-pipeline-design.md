# Plain-language translation pipeline — design

**Date:** 2026-09-23  
**Status:** review-locked — factcheck before style; extend style_check; LT $0; parity/status follow-up  
**Repo:** dlgrv/HowToLiveBetter (EN/RU/ES over Chinese source)

## Problem

Fidelity tools are strong; plain language was weak. Pilot §33 exposed jargon and calques. Plan review caught wrong assemble names, style-before-factcheck vs `factcheck.py`, and scope creep (parallel linter + parity/status).

## Non-goals

No CN rewrite; no Benefit/Sources simplify; no paid LT; no mass rewrite; no new `style_plain_lint.py`.

## Correct pipeline order (locked)

Same numbering as [implementation plan](../plans/2026-09-23-plain-language-pipeline.md#correct-pipeline-order-commands).

```text
1. make_digest.py <NN>
2. LLM translate units (ZH→ru|en|es) → §TAG§ / §SRC§ in workdir
3. Assemble (names not symmetric):
     RU: tools/assemble.py
     EN: tools/assemble_en.py
     ES: tools/assemble_es.py
4. verify.py — HARD
5. [optional] simplify plain-terms only (simplify-plain.md)
6. verify.py — MUST re-run after any plain rewrite
7. factcheck.py — AFTER re-verify, BEFORE style/LT
     --lang ru|en only (es N/A until extended)
     without --stdin-verdict → stdout judge_unavailable, exit 2
     gate fail|error or grounded=false → exit 1
     mock: --stdin-verdict '{"unit":"…","assertions":[],"issues":[]}'
8. style_check.py (WARN)
9. lt_check.py (self-host; down → WARN skip)
10. plainness (ru|en; no ES field yet)
11. human
```

Simplify-only shortcut: patch plain → verify → factcheck → style → lt → plainness → human.

**Forbidden:** LT/style before factcheck after simplify; `assemble_ru.py`; EN as RU/ES master.

## Quality pack

Pilot rules + high (abbrev, calques, factcheck) + medium (titles/Cost, sensitive, upstream checklist, number locale in prompts). Cross-locale parity tooling and status-line WARN → follow-up.

## Money

Docker LanguageTool only (LGPL, $0).

## Pilot

ch01 §33 **v3** = gold few-shot.
