# Simplify plain-terms only (one item or unit)

You rewrite **only** the plain-language field of an existing translation
(RU «Простыми словами», EN «In plain terms», ES «Términos sencillos»).
**Chinese (ZH) is the meaning anchor** — read the CN unit if provided.
Do **not** change Benefit, Cost, Sources, notes, tags, or URLs.

## Scope

- Input: assembled chapter text or a single item excerpt.
- Output: the same structure with **only** plain-terms lines edited.
- Numbers in plain-terms must remain a **subset** of Benefit (no new stats).

## Quality pack

Apply the same locked rules as `tools/prompts/translate-unit.md`:

1. Neighbor test.
2. Chemical gloss + `(term)` — no bare paraquat / lone herbicide /
   гербицид / herbicida.
3. Procedures stay in Benefit; plain-terms = outcome for the reader.
4. Correct place-name grammar (`name_forms` for RU).
5. 2–3 readable sentences; dual-topic = one sentence each + optional takeaway.
6. **Parallel outcomes** — two % in one ZH breath → full verbs both sides
   («шанс…ниже…, а вероятность…— ниже…»), not telegram ellipsis.
7. Closing caution follows ZH claim type («не считается» vs vivid
   «не поможет» only if still true).
8. No HR/RR/OR/CI in plain-terms.
9. Abbreviations / units: gloss on first plain-terms use
   (`abbrev_gloss_examples`: mmHg, ИМТ/BMI, КТ/CT, МРТ/MRI, УЗИ, HPV,
   ммоль/л, mg/dL). Skip ml / °C / SIM-PIN when obvious.
10. Avoid `banned_calques` patterns.
11. **No over-compress** — see «When not to simplify» below.

## Pipeline order (mandatory after your edit)

1. `python3 tools/verify.py <NN> --lang <lang>` — **must pass (HARD)**
2. **Factcheck vs ZH** — **before** style_check or LanguageTool
3. `style_check.py` (WARN; `--plain-only` when available)
4. `lt_check.py` (WARN)
5. `plainness` (ru|en)
6. Human pass

If verify fails, fix numbers or revert plain-terms before factcheck.
**Never** run style/LT as a substitute for factcheck.

## When not to simplify

- If Benefit already uses the only allowed numbers and plain-terms is
  empty or missing — flag for human, do not invent text.
- If simplifying would require moving clinical detail from Benefit into
  plain-terms, stop and leave Benefit unchanged.
- **Do not rewrite for rewrite's sake.** If the current plain-terms already
  passes the neighbor test, **leave the sentence shape alone**. Only fix
  real defects: jargon, calques, «примерно примерно», «семь десятых»,
  bare chemicals, wrong place-name case, telegraph-deleted parallel verbs.
- **Do not over-compress stats.** Prefer full natural phrasing over a
  shorter telegram.
  - Good (keep): «Только за 2025 год по всей стране было 828 случаев
    отравления грибами: 2165 пострадавших, 13 погибших.»
  - Bad (too tight): «Только за 2025 год по стране 828 отравлений
    грибами: 2165 пострадавших, 13 погибших.»
- **What to cut vs keep** (pilot ch01 §4–§5):
  - **Cut** (like §4): long official regulation titles → short gloss
    («правила городского газа» + CN name in parentheses); door-sales
    legalese → punchy refuse line.
  - **Keep** (like §5): already-clear incident counts and folk-myth
    lists; do not squeeze «было N случаев X» into «N X».

## Few-shot targets

1. **Tone / jargon** — ch01 §33 v3  
   (`docs/superpowers/pilots/2026-09-23-plain-01-item33.md`)
2. **Parallel %** — ch01 §2 preferred RU  
   (`docs/superpowers/pilots/2026-09-23-plain-01-item02-03.md`)
3. **Rewrite vs leave alone** — ch01 §4–§5  
   (`docs/superpowers/pilots/2026-09-24-plain-01-item04-05.md`):  
   §4 = good rewrite (legalese → neighbor); §5 RU = **keep book/ shape**
   («было 828 случаев отравления грибами…»), do not compress.

Do not copy unrelated items verbatim; match **density and clarity**.
Match ZH 说人话 rhythm when the locale draft is already clear.
