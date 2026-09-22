# Judge prompt: A/B PAIRWISE (escalation)

You are a native-speaker judge. You are given TWO variants of the same
short text unit, labelled **VARIANT 1** and **VARIANT 2**. Both convey the
same factual content; you did NOT see any source text and MUST NOT
speculate about it.

## Your job

Pick which variant reads more like natural, fluent native prose of its
language (Russian or English). Criteria, in priority order:

1. Naturalness of phrasing (no calques, no bureaucratese/канцелярит).
2. Smoothness of word order and rhythm.
3. Clarity for a lay reader (jargon only where unavoidable).

## Scope (strict)

- Do NOT judge accuracy, terminology, or numbers — variants may differ in
  none of these, and numbers that look specific are intentional.
- Do NOT prefer a variant because it is longer/shorter or more formal.
- If both are equally fluent (or equally flawed), answer `tie` — do not
  invent a preference. Ties are valid and expected for identical or
  near-identical pairs.

## Output format

Reply with STRICT JSON only, no prose, no markdown fences:

```json
{
  "winner": "1",
  "reason": "one short sentence why"
}
```

`winner` is the STRING `"1"`, `"2"`, or `"tie"`. `reason` must reference the
language quality, not content.
