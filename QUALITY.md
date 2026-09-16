# Translation quality rubric (MQM-based)

Scoring framework adapted from MQM (Multidimensional Quality Metrics, themqm.org).
Applies to every file in `book/en/` and `book/ru/`. Reviewers annotate errors per
item and compute a score; target threshold: **pass** (see below).

## Error dimensions and weights

| Dimension | What counts as an error | Weight |
|---|---|---|
| **Accuracy** | Wrong/altered numbers; dropped or added meaning; flipped negation; distorted HR/RR/OR/CI; "improved" claims not in the source; lost hedging («около», «примерно»); over/under-translation | CRITICAL ×5 |
| **Terminology** | Wrong medical/legal/statistical term (e.g. mammogram rendered as generic X-ray, "eradicate" → "treat", serodiscordant mistranslated); inconsistent term across the file | MAJOR ×3 |
| **Fluency** | Grammar, punctuation, garbled syntax, calques that are hard to parse | MINOR ×1 |
| **Style** | Tone mismatch (original is restrained, no moralizing, no exclamation marks); titles not verb-first; register breaks | MINOR ×1 |
| **Readability** (project-specific) | Applies above all to the «In plain terms / Простыми словами» line: it must read as natural speech, not a calque; a reader must grasp the takeaway in one pass; no sentences that need re-reading | MAJOR ×3 (for that line only) |

Severity multipliers: critical = 25, major = 5, minor = 1.

## Hard rules (automatic fail regardless of score)

1. Any number, DOI, URL, or citation altered or lost.
2. Any HR/RR/OR/CI value or confidence interval wrong.
3. Cost-tag comment `<!-- 成本标签: ... -->` not byte-identical.
4. Sources line not byte-identical after the field label.
5. Any LLM-invented content (facts, numbers, advice) absent from the source.
6. Missing status line / back-link / item count mismatch with the source.

## Score

```
score = 100 − (Σ penalty × weight) / (words / 1000)
```

Pass thresholds:
- Accuracy and Terminology: **zero** critical, **zero** major → hard requirement.
- Fluency + Style combined: score ≥ 95.
- Readability («plain terms» lines): score ≥ 95, no major.

## Verity (not an error)

Facts that are true for China but not the reader's country are NOT accuracy errors
when the file carries the China-context disclaimer. Do not "fix" them in
translation; translation is faithful, adaptation is out of scope.

## Review procedure

1. Read the source item, then the translated item, side by side.
2. Annotate every error with dimension + severity + exact location.
3. Compute the score; list all blockers from Hard rules.
4. Output: verdict per item (pass / fix), full file verdict, and a fix list with
   concrete suggested wording — not just "awkward".
