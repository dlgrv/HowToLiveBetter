# Expert review — translation-QA methodology, judge prompts, taxonomy, findings plausibility

Reviewer: adversarial domain review (translation-QA science + judge-prompt design)
Repo: HowToLiveBetter, branch `quality/pipeline-v2`, 2026-09-19. Read-only review; this file is the only artifact written.
Scope: `tools/prompts/judge-{screen,ab,factcheck}.md`, `tools/validate/golden_pairs.py`, `tools/validate/factcheck.py`, `tools/validate/judge_metrics.py`, `tools/validate/mutation_test.py`, `tools/validate/retro_e_report.py`, `tools/rules/{ru,en}.json`, results under `tools/validate/results/` + `tools/judge/factcheck/`, verified against `book/ru/11-*.md`, `book/ru/30-*.md`, `book/11-*.md`, `book/30-*.md`, `tools/digest/{11,30}/units/`.

Method: full read of the three prompts and the gate/orchestrator code; programmatic re-check of grounding and gate logic over all 98 verdicts / 594 assertions; length and order analysis of the 60-pair golden manifest and blind summary; regex experiments against the whole `book/ru` corpus; manual verification of the 3 grounded retro issues against CN/RU source texts; literature cross-check (MQM CORE typology; WMT QE 2023/2024 findings; LLM-as-judge bias literature: "Justice or Prejudice?" arXiv:2410.02736, self-preference arXiv:2410.21819, position-bias swap mitigation / GEMBA line of work).

**Verdict summary: the architecture is sound (source-blind fluency screen + source-grounded fact-check + mechanical numeric gate is the right separation, matching MQM Accuracy/Fluency split and WMT QE practice), but the validation evidence is thinner than it looks: the committed factcheck prompt does not match the deployed output contract (silent gate-bypass risk), the golden A/B set has a systematic verbosity confound and cannot distinguish fluency sensitivity from self-preference, the grounding gate proves existence not entailment, and one style rule does not implement its stated semantics.**

Severity counts: **1 critical, 9 major, 7 minor** (17 findings).

| # | Sev | Area | Finding |
|---|-----|------|---------|
| F1 | CRIT | factcheck | Prompt/output contract drift: gate keys on fields the committed prompt never asks for |
| F2 | MAJ | factcheck | Grounding gate = existence, not entailment → fabricatable findings pass (evidence: 11-ru-00) |
| F3 | MAJ | factcheck | Verbatim-span gate too brittle: ellipsis spans and paraphrases auto-dropped |
| F4 | MAJ | judge-ab | A/B-vs-degradation does NOT offset self-preference (GLM judges GLM output) |
| F5 | MAJ | golden | Verbosity confound: all 50 degraded B variants are longer than A (mean +8.3%) |
| F6 | MAJ | judge-ab | Position bias unmeasurable by design; prompt example anchors "winner": 1 |
| F7 | MAJ | golden | Degradation recipes miss the pipeline's actual historical defect class (lexical calques) |
| F8 | MAJ | taxonomy | No `hardened_claim` (mirror of `softened_claim`); overlaps without precedence rules; `cross_unit_contradiction` unobservable at unit granularity |
| F9 | MAJ | ru.json | "причастная цепочка" regex matches plain adjective pairs, misses genitive chains |
| F10 | MAJ | retro | Same translator meta-note gated differently: ch11 u00 warn vs ch28 u00 excused |
| F11 | MIN | screen | Enum typo `bureacratese` |
| F12 | MIN | judge-ab | `winner` typed int vs string `"tie"` |
| F13 | MIN | metrics | Decoy control vacuous in `golden_blind_summary.json` (ties counted as unanswered) |
| F14 | MIN | docs | Protocol/manifest drift: planned chapters ≠ GREEN_CHAPTERS; labels file absent, κ pending |
| F15 | MIN | coverage | EN essentially unvalidated: 19/50 golden pairs, 0 EN pass-E verdicts |
| F16 | MIN | ru.json | `banned_calques` bans standard Russian terms — house style, not error |
| F17 | MIN | mutation | Catch-rate protocol (≥80% catch, ≤10% FP) designed but not yet executed |

---

## Critical

### F1. Factcheck prompt/output contract drift — gate can silently pass everything
`tools/prompts/judge-factcheck.md` specifies per-assertion output `{cn_span, claim, ru_ok, en_ok, issue_type, detail}`. The 98 live verdicts (594 assertions) contain none of `ru_ok`/`en_ok`; instead every assertion carries `status: "ok"|"issue"` plus a top-level `unverifiable` list — fields that appear nowhere in the committed prompt. `factcheck.gate_major()` keys exclusively on `a.get("status") == "issue"`.

Consequences:
- Either the live waves ran an unversioned prompt variant, or the judge deviated from the committed schema 594/594 times — both mean the committed prompt no longer describes the deployed protocol, and `prompt_hash` reproducibility (pinned in `factcheck.write_result`) is not actually pinned for these runs (the wave verdict files don't even carry it; keys are `chapter, lang, unit, model_id, ts, assertions, unverifiable`).
- If a future judge follows the committed prompt literally (`ru_ok/en_ok`, no `status`), `gate_major()` computes `major=[]` for every unit → **every chapter gates `pass` with no error and no warning**. A correctness gate that fails open on schema drift.

Fix: make one schema authoritative. Add `status` + `unverifiable` to `judge-factcheck.md` (or switch gate to `ru_ok==false or en_ok==false`), validate verdict JSON at ingest (reject assertions lacking `status`+`issue_type` when `status=="issue"`), and store `prompt_hash` in the wave verdict records. Add a unit test that runs `gate_major` against a verdict produced *from the committed prompt text*.

## Major

### F2. Grounding gate checks span existence, not span→claim relevance
`factcheck.check_grounding()` keeps any assertion whose `cn_span` is a verbatim (or whitespace-normalized) substring of the CN body. That defeats fabrication of the *span* but not fabrication of the *claim*: the judge can attach any invented issue to any real span.

Evidence — this happened: `tools/judge/factcheck/11-ru-00.json`, the chapter-11 `added_advice` finding, is grounded on span `每条给出法条里的数字和最高检、最高法官网公布的案例` ("each item gives numbers from statute articles and cases published on SPP/SPC sites"). The span is verbatim and passes the gate (`grounded: true` in `retro_e_findings.json`), but it says nothing about a disclaimer; the claim ("RU added a reference-only warning absent from CN") is evaluated against the whole unit, not the span. Since `added_advice` only produces a `warn` today, impact was bounded — but the identical mechanism attached to `reversed_logic`/`invented`/`dropped_condition` produces a hard chapter **FAIL**.

Related hole: the `unverifiable` side-channel is copied into the retro report unaudited (`retro_e_report.py:68`); any finding can be parked there with zero gate consequence (see 28-ru-04's machine-specific access claim).

Fix: (a) second-stage relevance check — mechanically cheap version: require the judge to also emit a one-line `span_supports_claim: true|false` and drop `false`; stronger version: a separate verifier pass per kept issue ("does this span support this claim?") before the gate; (b) aggregate and audit `unverifiable` like issues (at least count and surface them in the retro report per unit).

### F3. Verbatim-span requirement is too brittle for legitimately grounded findings
The ≥4-char contiguous-verbatim rule (plus whitespace-collapse fallback) drops real assertions when the judge quotes with ellipsis or paraphrase. Of 594 assertions, 5 were dropped; at least 2 (`30-ru-02`: span containing `……`; `13-ru-19`: span containing `…`) fail *only* because of ellipsis inside an otherwise verbatim quote — the CN source genuinely contains both fragments. A judge that summarizes (which you want for multi-line omissions) is punished; a judge that quotes an unrelated span is rewarded (F2). The current rule selects for the wrong quoting behavior.

Fix: normalize ellipsis variants (`……`/`…`/`...` → one token) before matching; allow the judge to supply up to 2–3 alternative spans per assertion and keep the assertion if any grounds; optional final fallback: fuzzy containment ≥0.85 char-bigram overlap, flagged as `fuzzy_grounded` in the audit record. Keep the verbatim-first rule — it is the right default; these are escape hatches, not relaxations of the service-line exclusion (which is correctly positional and verified sound: no digest unit has content after `§SRC§`).

### F4. A/B-against-controlled-degradation does not offset self-preference
The judge is `glm-5.3-flash` (`tools/rules/project.yaml`) and the translations being judged are GLM-family output (same model family produced the translation waves and the degradation variants in `tools/validate/results/_ru_work/degrade.py`). The literature is clear that LLM judges systematically favor their own family's outputs (self-preference/self-enhancement bias; arXiv:2410.21819 shows the effect tracks low judge-perplexity of the candidate, i.e. it operates on *any* fluent text, not only text the judge authored). In this design both A and B are GLM-flavored (B = degraded GLM A), so "judge prefers A" is consistent with two incompatible explanations: real fluency sensitivity, or own-style preference. The golden result — 50/50 native picks, decoys 10/10 tie (`golden_blind_summary.json`) — cannot separate them. The decoys only rule out position/tie-break artifacts, not self-preference.

What *does* mitigate: the protocol's pass D (local Qwen, a different family) and the human kappa anchor (κ≥0.6 gate in `docs/validation-protocol.md` Step 3) — cross-family agreement plus human labels is the standard mitigation. Those are planned, not yet measured (`golden_labels.json` absent).

Fix: (a) treat the degradation-golden result as a *floor* (sensitivity), never as evidence of unbiasedness; (b) generate a golden subset of B-variants with a non-GLM model or by the human editor, so the judge's preference can't align with family style; (c) report judge↔judge agreement split by family, and make the human kappa the decisive validation, as the protocol already intends.

### F5. Verbosity confound baked into the golden set
Measured on `golden_manifest.json`: **all 50** filled non-decoy B variants are longer than A (mean relative length delta +8.3%, min +1.5%, max — all positive; B shorter: 0). The four degradation recipes (insert officialese, stack passives, literalize, impersonalize) all systematically add words. The judge-ab prompt forbids preferring length, but a crude "prefer the shorter variant" heuristic alone reproduces the observed 100% native rate. Verbosity bias is one of the best-documented judge biases (arXiv:2410.02736). With a length-monotone golden set you cannot tell sensitivity to канцелярит from length preference, and any future recalibration on these pairs inherits the confound.

Fix: constrain the recipes to be approximately length-neutral (compensate insertions with equivalent deletions, target |Δ| ≤ 2%); add an explicit length-balanced stratum to the manifest; report correlation between per-pair length delta and choice in `judge_metrics.py` (a nonzero correlation is a direct bias readout).

### F6. Position bias: unmeasurable by design + anchoring example
Each pair is judged exactly once, in the single `show_order` pinned at generation time (`golden_pairs.py:89`). Randomization across pairs balances the estimate at the population level, but with zero within-pair variance the design cannot detect order-dependent flipping for any individual pair — the standard mitigation is judging each pair (or a large subsample) in both orders and requiring consistency (swap test; cf. Wang et al. 2023, "Large Language Models are not Fair Evaluators"; systematic position-bias studies, IJCNLP 2025). Additionally the prompt's output example is `{"winner": 1, ...}` — few-shot anchoring toward answering 1; with 22 answers of `1` in the golden run this is not hypothetical.

What's already right: ties are explicitly licensed ("Ties are valid and expected"), and the 10 A=B decoys all got `=` — the gross false-preference control passed. That control has a blind spot though: it only catches tie-breaking failure on *identical* texts, not order sensitivity on *different* ones.

Fix: re-judge a ≥30-pair subsample in both orders, require consistency or downgrade to tie; neutralize the example (`"winner": 2`, or no concrete value); keep decoys.

### F7. Degradation recipes don't cover the failure modes this pipeline actually had
All four recipes are syntactic-register degradations (impersonal calque, literalisation, bureaucratese, passive chain). The pipeline's documented real defects are different: lexical latinisms/calques — `когорт` ×13, `популяц` ×2 (retro known-defects), and 67 calques/office-speak fixed in the style pass (`git log`: "naturalness pass — fix 67 calques/office-speak"). None of the recipes produces a lexical calque like `когортное исследование` for `队列研究`, nor CN-specific transfer structures (topic-prominent word order, 是…的 calques) — the corpus is CN→RU, but the recipes read like EN→RU officialese catalogs. A judge can score 100% on this golden set and still be blind to the defect class that triggered the whole style pipeline.

Fix: add a `lexical_calque` recipe seeded from the actual fix history (the retro known-defect fragments are the ideal seeds — they double as the recall anchor for style rules); optionally a `register_shift` recipe (too colloquial for the book's voice). Keep numbers byte-identical as now — excluding numerals from scope to avoid verify.py overlap is correct and well-implemented.

### F8. Taxonomy: asymmetric hedge coverage + overlaps without precedence + unobservable class
Against MQM CORE (Accuracy = Mistranslation / Addition / Omission / Untranslated), the 7 semantic classes are a reasonable operational flattening for this book's risk profile, and most are cleanly definable. Gaps:

- **No `hardened_claim`.** `softened_claim` exists ("снижает на 20%" → "может снижать") but its mirror — dropping a CN hedge or upgrading may→does — has no class. The retro's own ch30 u06 finding (hedge `一般` dropped, RU states a hard norm) is exactly this, currently forced into `dropped_condition`. Since the gate treats `softened_claim` as minor (warn) while `dropped_condition` is major (fail), the *same meaning change* is gated at different severity depending on which direction the hedge moved. Add `hardened_claim` and put both in the same severity tier.
- **`invented` vs `added_advice`**: added advice *is* invented propositional content (11-ru-10 «отсудила» could be filed under either). Needs a precedence rule, e.g. `invented` when new factual/propositional content, `added_advice` only for deontic/recommendatory content.
- **`subject_swapped` vs `reversed_logic`**: swapping agent/patient usually flips direction. Precedence: `reversed_logic` when the causal/deontic direction flips, `subject_swapped` when participants exchange with direction intact.
- **`cross_unit_contradiction`**: the prompt honestly says "only when both texts are visible to you" — but in deployment pass E sees one unit, so the class is never observable; meanwhile `mutation_test.build_cases()` feeds whole chapters (evaluation condition ≠ deployment condition, a distribution shift that inflates the mutation catch-rate precisely on this class).

Fix: add `hardened_claim`; write the precedence rules into the prompt (one sentence each); either give pass E a chapter-map digest of sibling-unit claims or drop the class from the unit prompt and keep it chapter-level only — and make the mutation harness match whatever deployment does.

### F9. `ru.json` "причастная цепочка" regex does not implement its label
Label: "две страдательные причастные формы подряд". The pattern `[а-яё]{4,}(нн|ем|им)(ый|ая|ое|ым|ом|ые|ых|ыми)\s+…` in fact matches *any* two adjective-final forms: verified false positives in `book/ru` include «единственная переменная», «собственных законных», «инвестиционное пенсионное», «неизменном ожидаемом», «государственных централизованных» — plain adjectives, no participles. It also *misses* true participial chains in the genitive («выполненного настроенного» — `-ого/-его/-ому/-ему` endings are absent from the list). Corpus scan: 27 hits, roughly half benign adjective pairs; 18 of 27 fall on whitelisted lines anyway (`- Эффект:` etc.). WARN-only status keeps this from blocking, but the protocol's recall anchor (≥60% of known-bad fragments per rule class, Step 4) will be measured against a rule whose precision/recall profile doesn't match its stated semantics.

Fix: either implement the label (restrict to participial suffixes `-нн-/-енн-/-т-` + short-form checks, add oblique-case endings) or relabel the rule to what it matches ("adjective-pair stacking") and tune expectations accordingly. Cheap intermediate: require the first token to contain `-нн-`/`-енн-` and exclude a stoplist of frequent non-participial adjectives (`единственн-`, `переменн-`, `законн-`, `пенсионн-`…).

### F10. Retro gate inconsistency: identical translator meta-note, opposite treatment
The ch11 u00 `added_advice` (RU intro disclaimer «Глава 11 ссылается на китайские законы и учреждения; для читателей вне Китая это справочный материал…», absent from CN intro — verified in `book/ru/11-*.md` vs `book/11-*.md`) was gated as a real issue (chapter warn). The *same kind* of standalone reference-only disclaimer in ch28 u00 was explicitly excused in the verdict's `unverifiable` ("translator/edition meta-notes without a CN counterpart, not judged as added_advice"). Both cannot be right. Either translator meta-notes are in scope (then ch28 was under-flagged) or out of scope (then ch11's warn is a false positive and the chapter gate should be pass). Compounding it, the ch11 finding's `cn_span` is unrelated to the claim (F2).

On plausibility of the three sampled issues overall — **all three are real RU↔CN discrepancies, verified against source**:
- **11-ru-10 `invented` — confirmed, correctly classified.** RU «Простыми словами»: «фармацевтическая компания **отсудила** у своего технического директора 7,1 млн юаней неустойки»; CN: 告首席技术官**索赔** 710 万元违约金 … **全部驳回** (filed a claim; court dismissed it entirely). «Отсудила» asserts winning the case — no basis in CN and contradicted by the same RU sentence («отклонила иск целиком»). Genuine, gate-worthy.
- **30-ru-06 `dropped_condition` — confirmed real; class debatable.** CN «每名学生每学年接受心理测评**一般**不超过 1 次»; RU: «каждый ученик проходил психологическое тестирование **не чаще 1 раза** в учебный год». The hedge 一般 ("as a rule") is dropped, hardening the norm. Real discrepancy; per F8 it is really a hardened claim, which is why the taxonomy gap shows up in the retro data itself.
- **11-ru-00 `added_advice` — the addition is real, the gating is not (F10).**

The 591 ok-assertions sampled (10-ru-*, 13-ru-15/19, 30-ru-00/02, 11-ru-15) are accurate, appropriately conservative paraphrase-level claims; the 5 ungrounded drops are span-mechanics, not judge errors (F3). One caveat on interpreting the retro report: 594 assertions / 3 issues (0.5%) with 95/98 pass gates says "the judge found almost nothing", and E's miss-rate is still unquantified until F17 runs — pass-rate should not be quoted as cleanliness evidence yet.

Fix: write the scope rule into `judge-factcheck.md` ("translator prefaces, glosses «(рус. …)», and reference-only disclaimers are out of scope; added in-body recommendations/warnings are `added_advice`"), then re-run `retro_e_report.py` — expect ch11 gates to change.

## Minor

### F11. Screen prompt enum typo
`judge-screen.md` issue type enum: `calque|bureacratese|awkward|grammar|other` — "bureacratese" is misspelled (missing 'u'). Judges copying the enum emit the typo into verdict data; downstream consumers keying on the correct spelling will silently miss them. Fix the string, and pin the enum in the ingest validator.

### F12. `winner` type inconsistency in judge-ab
Schema says `winner` is `1`, `2`, or the *string* `"tie"`; the example shows an int. Parsers must special-case mixed types (the golden batches do: ints + `'='`). Use strings `"1"|"2"|"tie"` consistently, and accept `=`/`0` on ingest for robustness.

### F13. Decoy metric vacuous in the blind summary
`golden_blind_summary.json` reports `decoy_detail.answered: 0`, `decoy_fp_rate: null`, `unanswered: []` — yet all 10 decoys *were* answered `=`. The aggregator counts ties as unanswered, so the attention-control reads as "never ran" instead of "10/10 correct ties". Fix the counter (`'='` → answered-tie) so the control metric is actually reported; a null FP rate must not be interpretable as a pass.

### F14. Protocol/doc drift
`docs/validation-protocol.md` Step 2 pins golden chapters 01/10/13/16/24/30; `GREEN_CHAPTERS` in `golden_pairs.py` excludes 10/13/30 (defensible — they are known-defect chapters and would contaminate clean anchors — but the deviation is undocumented). The κ-vs-Лёня flow references `results/golden_labels.json`, which does not exist yet, so `judge_metrics.py` currently reports pending. Sync the doc with the implemented exclusion and mark the human-label step as outstanding.

### F15. EN is essentially unvalidated
Golden set: 19/50 non-decoy pairs are EN (anchors 3/stratum vs RU 6); `en.json` carries 4 style markers vs RU 5 plus a corpus-frequency audit; pass E ran only RU waves — 0 `*-en-*.json` verdicts, `en_ok: null` never exercised. Any claim of pipeline validity for the EN edition currently rests on extrapolation. Fix: rebalance golden sampling toward ~25/25 and schedule the EN pass-E wave before the next retro report.

### F16. `banned_calques` conflates house style with error
«популяция», «квартиль», «когорта», «экспозиция», «конфаундер»-derivatives are standard Russian statistical/epidemiological vocabulary; banning the stems is a deliberate plain-language house choice for this book (defensible for the register, and correctly WARN-priority). Risk: the list's name and its placement in `verify.py` invite reuse as a general "error" list in other projects, where it would flag correct technical Russian. Fix: rename/comment as `house_style_avoid` and keep it project-scoped; same for the EN pack's duplicated `aforementioned` patterns (two overlapping regexes, one a substring of the other).

### F17. Mutation validation designed but not yet executed
`mutations_seed42.json` is complete and structurally valid (30 mutations, 5 per class, +30 controls, excerpts verified in-book, seed_ref pinned), and the accept thresholds are sensible (catch ≥80%, FP ≤10%, novelty vs verify ≥70%). But no mutant verdicts exist in results, so pass E's sensitivity is currently asserted, not measured — and the retro report's 95/98 pass gates are being read in that vacuum. Until the catch-rate run happens, the factcheck gate's true operating point is unknown. Also note F8's caveat: if the mutation harness feeds whole chapters while deployment feeds units, the measured catch-rate will overstate deployment performance for `cross_unit_contradiction`. Fix: run the harness through the same unit-level path as the live waves.

---

## What is already right (kept deliberately, do not "fix")
- Three-way separation of concerns (mechanical numerals in verify.py / source-blind fluency in C-D / source-grounded semantics in E) mirrors MQM Accuracy-vs-Fluency and avoids the classic QE overlap problem; the explicit "pure numeric mismatches are OUT OF SCOPE" clause in judge-factcheck is exactly the dedup discipline WMT QE findings recommend.
- Source-blind screen/AB prompts correctly forbid speculating about a source and forbid accuracy judgments — this prevents the judge from inventing a source, a real failure mode in reference-free judging.
- Decoys (A=B, 10/60) with an explicit tie license, `show_order` randomization, and mapping-never-in-markup (`variant→original` only in the manifest) are the right anti-leak primitives.
- Positional (line-start) service-line exclusion in `check_grounding` is correctly implemented and avoids the naive substring-marker trap (`出资来源` in body text stays, a span *on* a 来源 line is dropped); no digest unit carries content after `§SRC§`.
- `known_defects` cross-check in `retro_e_report.py` (numbers→verify, calques→style) shows correct domain ownership and honest negative controls.

## Literature anchors
- MQM CORE typology (Accuracy: Addition/Omission/Mistranslation/Untranslated; Fluency separate) — themqm.org; the 7-class semantic flattening is defensible but needs the precedence rules of F8.
- WMT QE shared tasks 2023/2024 findings: shift toward fine-grained, actionable, reference-free error detection; LLMs closing the gap on sentence-level QE — supports pass E's span-grounded design and the numeric-gate dedup.
- LLM-as-judge biases: position/verbosity/self-preference quantified in "Justice or Prejudice?" (arXiv:2410.02736); self-preference tracks judge perplexity of the candidate (arXiv:2410.21819) → F4/F5/F6; swap-consistency mitigation from the "LLMs are not Fair Evaluators" line → F6.
- GEMBA/GEMBA-MQM: LLM judges are best at source+target error *annotation* with strict output contracts → reinforces F1 (contract must be exact) and the choice of structured JSON over free-text verdicts.
