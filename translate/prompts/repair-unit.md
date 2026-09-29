# Repair one digest unit (targeted fix for verify HARD fails)

You repair **one already-translated work unit** so that machine verify passes.
This is NOT a re-translation: keep the existing translation as close to
verbatim as possible and change ONLY what the listed issues require.

## Rules

1. **Fix only the listed issues.** Do not rewrite unrelated sentences,
   re-order fields, or "improve" style. Grammar of an edited sentence may be
   adjusted, nothing more.
2. **number_absent:** the translation dropped or mis-scaled an absolute value
   that the Chinese unit contains. Restore it using the scale table:

   | ZH | Meaning | Example |
   |----|---------|---------|
   | 万 | ×10,000 | 61 万 = 610 000 |
   | 亿 | ×100,000,000 | 2 亿 = 200 000 000 |

   Do NOT map 亿 to «миллиард» (×10⁹) — it is ×10⁸. Write the number the way
   natural prose in the target locale writes absolute values
   (RU: «610 000 человек» or «более 61 тысячи человек» only if the check
   value 610000 matches — prefer exact absolute digits when unsure).
   Never invent a number that is not in the Chinese unit.
3. **banned_calque:** the stem (e.g. «популяц») appears too many times.
   Replace every occurrence except at most one first-use gloss — prefer
   replacing ALL of them when a natural alternative exists
   (RU alternatives: население / люди / жители; когорт → группа;
   экспозиция → воздействие). Keep meaning identical.
4. **Structure is sacred:**
   - First line stays `### N. Title` (same number and essentially same title).
   - Field lines stay dashed `- Label:` — NEVER bold `**Label:**`.
   - Keep the same set of field lines (Стоимость / Простыми словами / Эффект /
     Уровень доказательности / Примечания, or the EN/ES equivalents).
   - Do NOT output `§TAG§` or `§SRC§` — the pipeline injects them.
5. **Numbers are frozen** unless the issue list says otherwise: every other
   numeric value in the unit must survive unchanged (same values; RU/ES
   decimal comma is fine).
6. Output ONLY the repaired unit markdown — no fences, no preamble, no
   explanations.
