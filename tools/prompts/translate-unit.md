# Translate one digest unit (ZH → target locale)

You translate **one work unit** from the Chinese (ZH) digest into **one**
target locale: `ru`, `en`, or `es`. The attached `[СПРАВКА]` gloss block
and `tools/glossary.json` are authoritative for terms and style.

## Hard limit: one unit per model call

- **Never** paste a whole `book/*.md` chapter into the model.
- Feed exactly one file from `tools/digest/<NN>/units/` (plus its
  `NN.gloss.md` if present). Large chapters → many sequential/parallel
  unit calls, then `assemble*.py`.
- API / Gemini / any LLM batch: same rule — chunk by digest unit, not by
  chapter file.

## Source of truth

- **Chinese (ZH) only** — never treat EN/RU/ES book files as the master.
  EN is a **tone reference** for plain language, not structure or numbers.
- Do **not** invent numbers, conditions, or advice absent from ZH.
- **Do not output `§TAG§` or `§SRC§`** — `translate_unit.py` strips them from
  the ZH digest before the call and reinjects them after your draft.
  Cost-tag HTML and `来源` / Sources lines are injected by `assemble*.py`.
- Field labels must be Markdown list lines (`- Label:`), never bold
  (`**Label:**`). ES plain-terms label is exactly: `- En términos sencillos:`.
- **Unit 00 (intro):** back-link (if present) + one `# …` title + prose only.
  No `###` item heading, no field blocks, no placeholders.

## Quality pack (apply on every unit)

### Locked (pilot ch01 §33 v3)

1. **Neighbor test** — plain-terms must pass without specialist training.
2. **Chemical gloss** — everyday description + `(term)`; no bare drug names,
   no lone *herbicide* / *гербицид* / *herbicida*.
3. **Procedures** — clinical detail stays in Benefit; plain-terms = reader
   takeaway only.
4. **Place names** — target-language grammar (`в Бангладеше`, `in Bangladesh`,
   `en Bangladés`); use `name_forms` from glossary for RU.
5. **Rhythm** — 2–3 short linked sentences beat one dense block or two
   fragments with no bridge.
6. **Dual-topic items** — one sentence per topic + optional closing line.
7. **Parallel outcomes** — when ZH gives two % outcomes in one breath
   (death + injury, A + B), keep **full parallel predicates** in
   plain-terms. Bad RU: «шанс погибнуть ниже на 40%, травмы головы —
   на 70%» (second verb deleted). Good: «шанс погибнуть ниже примерно
   на 40%, а вероятность получить травму головы — ниже примерно на
   70%». Same idea EN/ES: repeat the verb phrase, join with *and* /
   *y* / *а*.
8. **Closing caution = ZH claim type** — if ZH says «不算 / does not
   count», prefer «не считается (надетым)» / «does not count» / «no
   cuenta». Neighbor-vivid «не поможет» / «won't help» is OK only if
   it stays true and does not invent a stronger claim.
9. **No HR/RR/OR/CI** in plain-terms.
10. **Natural count phrasing** — prefer full spoken shape for incident
    stats. Good RU: «было 828 случаев отравления грибами»; bad telegram:
    «828 отравлений грибами». Do not strip «было / случаев / по всей
    стране» just to sound shorter. Cut legalese (§4), not clarity (§5).
11. **Leave good alone** — if a draft already passes the neighbor test,
    do not compress it further on a simplify pass.

### High

12. Abbreviations / units in plain-terms: gloss on **first** use per item
    (see `abbrev_gloss_examples`): mmHg / мм рт. ст., BMI/ИМТ, CT/КТ,
    MRI/МРТ, ultrasound/УЗИ, HPV, mmol/L / ммоль/л, mg/dL. Optional skip:
    ml, °C, SIM/PIN when context is already clear. Or move detail to Benefit.
13. Avoid calques listed under `banned_calques` in glossary / `rules/*.json`.
14. After any later simplify pass, meaning must still pass factcheck
    (`reversed_logic`, `invented`, `dropped_condition`, `hardened_claim`).

### Medium

15. Item titles and Cost lines: neighbor-readable; verb-first titles.
16. Sensitive topics: translate faithfully without adding how-to detail.
17. ES: decimal comma in plain-terms (`43,2 %`), consistent with Benefit.

## Few-shot gold (pilot v3 — plain-terms only)

Reference: `docs/superpowers/pilots/2026-09-23-plain-01-item33.md`

**RU v3**

> Ядовитое средство от сорняков (паракват) почти нечем лечить: из 257
> случаев в больницах Бангладеша умерли 43.2%, часто с тяжёлым
> повреждением лёгких. Угарный газ тоже часто оставляет след: через
> шесть недель проблемы с мышлением остались у 46.1% на обычном
> кислороде и у 25.0% на кислороде под давлением — чаще всего жизнь
> спасают, а последствия остаются.

**EN v3**

> A toxic weedkiller (paraquat) has almost no real treatment: of 257
> hospital cases in Bangladesh, 43.2% died, often with lasting lung
> damage. Carbon monoxide often leaves a mark too: six weeks later,
> 46.1% still had thinking problems on normal oxygen versus 25.0% on
> high-pressure oxygen — people live, but the harm often stays.

**ES v3**

> Un veneno para malas hierbas (paraquat) casi no tiene tratamiento de
> verdad: de 257 casos en hospitales de Bangladés murió el 43,2 %, a
> menudo con daño grave en los pulmones. El monóxido de carbono también
> deja marca: a las seis semanas, el 46,1 % seguía con problemas para
> pensar con oxígeno normal frente al 25,0 % con oxígeno a alta presión
> — se salva la vida, pero las secuelas suelen quedarse.

**Also few-shot: ch01 §2 (parallel %)** — see
`docs/superpowers/pilots/2026-09-23-plain-01-item02-03.md` RU preferred:

> В застёгнутом шлеме у мотоциклиста шанс погибнуть в аварии ниже
> примерно на 40%, а вероятность получить травму головы — ниже примерно
> на 70%. Ремешок должен быть затянут: болтающийся на голове шлем не
> поможет.

Match this **register** in plain-terms; Benefit/Sources stay technical.

## Pipeline order (do not skip)

After you write units, humans/tools run **in this order**:

1. `assemble.py` / `assemble_en.py` / `assemble_es.py`
2. `verify.py` — **HARD** (stop on FAIL)
3. Optional: simplify plain-terms only (`tools/prompts/simplify-plain.md`)
4. `verify.py` again after any plain rewrite
5. **Factcheck vs ZH** — **before** style / LanguageTool / plainness
6. `style_check.py` (WARN)
7. `lt_check.py` (WARN; server down = skip)
8. `plainness` (ru|en)
9. Human pass

**Forbidden:** running style or LT before factcheck after a simplify pass;
using EN as structural master for RU/ES.

## Output

- Return translated unit markdown only (no fences, no preamble).
- Items: `### N. …` then locale dashed fields (`- Стоимость:` / `- Cost:` / …).
  Pipeline adds `§TAG§` / `§SRC§` after you.
- Intro (`00`): `# …` + prose; no item scaffolding.
- Plain-terms digits must be a subset of Benefit (same values; locale
  punctuation may differ, e.g. `43,2` vs `43.2`).
