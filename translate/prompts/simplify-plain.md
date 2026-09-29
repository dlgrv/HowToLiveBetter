# Simplify plain-terms only (one item or unit)

You rewrite **only** the plain-language field of an existing translation
(RU «Простыми словами», EN «In plain terms», ES «En términos sencillos»).
**Chinese (ZH) is the meaning anchor** — read the CN unit if provided.
Do **not** change Benefit, Cost, Sources, notes, tags, or URLs.

## Scope

- Input: **one digest unit** (or a single-item excerpt). Never feed a whole
  chapter markdown file into the model — use `translate/digest/<NN>/units/NN.md`.
- Output: the same structure with **only** plain-terms lines edited.
- Numbers in plain-terms must remain a **subset** of Benefit (no new stats).

## Quality pack

Apply the same locked rules as `translate/prompts/translate-unit.md`:

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
10. Avoid `banned_calques` / `soft_calques` patterns from `translate/rules/<lang>.json`.
11. **No over-compress** — see «When not to simplify» below.

## Pipeline order (mandatory after your edit)

1. `verify` — **must pass (HARD)**. If it fails, stop polish and run repair.
2. Clarity again (`понятно` / `непонятно` on plain-terms). Leftover `непонятно` goes to a human list.

Do not run style or LanguageTool inside the polish loop (they run before polish).

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

1. **Tone / jargon** — ch01 paraquat/CO plain-terms (see `translate-unit.md` few-shot)
2. **Parallel %** — ch01 helmet item, preferred RU (same few-shot block)
3. **Rewrite vs leave alone** — ch01: legalese → neighbor OK; keep book/ shape for
   clear incident counts («было 828 случаев отравления грибами…»), do not compress.

Do not copy unrelated items verbatim; match **density and clarity**.
Match ZH 说人话 rhythm when the locale draft is already clear.
