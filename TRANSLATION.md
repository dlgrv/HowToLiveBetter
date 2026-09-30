# Translation conventions (EN / RU / ES / PT / …)

Applies to everything under `book/<lang>/` for non-Chinese locales (see [docs/pipeline/add-language.md](docs/pipeline/add-language.md); registry: [translate/langs.json](translate/langs.json)). Chinese originals live at `book/*.md`.

## Status line
First line of every translated file, before the back-link:

```
> Unofficial translation of [book/01-不要早死.md](../01-不要早死.md). In case of any discrepancy the Chinese original prevails.
```
(RU: «Неофициальный перевод файла book/01-….md. При расхождениях приоритет у китайского оригинала.»)

## Keep untouched
- Full citation lines in `- 来源：/来源` — author names, journal names, DOIs, URLs, Chinese regulation titles + document numbers stay exactly as in the original. Only the surrounding field label is translated.
- All numbers, HR/RR/OR/CI values, percentages, prices. Locale *spelling* of the same absolute value is fine (RU/ES/PT decimal comma `0,499`; never drop the point as `0499`). Pipeline may append `〔N〕` in Notes when verify needs a missing abs value — see [translate/steps/repair/mechanical.py](translate/steps/repair/mechanical.py).
- The HTML cost-tag comment `<!-- 成本标签: ... -->` — keep the Chinese field names (钱/时间/毅力/收益/口径) and values byte-identical; index.html parses it.
- Markdown structure: heading levels, `### N.` numbering, list-item order, links.
- Field text stays on the **same line** as `- Label:` (no bare empty label with value on the next line).

## Translate
- Field labels (SSOT: `translate/rules/<lang>.json` via `translate.lib.labels`):

  | CN | EN | RU | ES | PT |
  |---|---|---|---|---|
  | 成本 | Cost | Стоимость | Costo | Custo |
  | 说人话 | In plain terms | Простыми словами | En términos sencillos | Em linguagem simples |
  | 收益 | Benefit | Эффект | Beneficio | Benefício |
  | 证据等级 | Evidence grade | Уровень доказательности | Nivel de evidencia | Nível de evidência |
  | 来源 | Sources | Источники | Fuentes | Fontes |
  | 备注 | Notes | Примечания | Notas | Notas |

- The «说人话» line is the most important line — translate it fully and idiomatically; it may not introduce numbers absent from the 收益 line.
- Units: 元→CNY (keep "yuan" also acceptable in RU: «юаней»); keep mmHg, mg, %, etc. Chinese administrative terms (医保, 户口, ICP 备案, 疾控中心) → transliterate or translate with the Chinese term in parentheses on first use in a file.
- Law/regulation names: translate the meaning + keep the official Chinese name and document number in the sources line (already there); in body text give an English/Russian gloss.
- Translator's additions (localization) must be clearly marked INSERTIONS — never edit or replace original content:
  - **Translator's note block** (`> Примечание переводчика: …`) under the chapter heading, for chapter-wide country-specific facts (emergency numbers, units, institution names). Allowed additions: RU/112 and 911 mappings for Chinese emergency numbers, unit hints, one-line "what this Chinese institution is".
  - **In-line gloss** on first use per chapter: `термин (中文 — короткое пояснение)` for China-specific concepts (дибао 低保, хукоу 户口, …). The Chinese term + meaning must come from the original; no invented facts.
  - **Glossary** in `README.ru.md`: terms that recur across chapters (дибао, хукоу, 医保…) get a one-line entry; chapters gloss on first use and stay short afterwards.
  - Verification scripts must tolerate these insertion patterns (strip `> Примечание переводчика` blocks and `(中文 …)` glosses before counting hanzi/numbers).

## RU file naming

Files under `book/ru/` are renamed to Russian slugs (localization of filenames):
`book/ru/<NN>-<Заголовок-через-дефисы>.md`. Keep the two-digit chapter prefix (sort order),
no spaces, proper Russian, ё allowed. The status line inside the file still links to the
Chinese original (`../01-不要早死.md`) — that link must not change.

| Ch | Slug |
|---|---|
| 01 | 01-Не-умирайте-рано |
| 02 | 02-Не-умирайте-медленно |
| 03 | 03-Не-тратьте-силы-зря |
| 04 | 04-Не-тратьте-время-впустую |
| 05 | 05-Не-тратьте-деньги-впустую |
| 06 | 06-Анти-список |
| 07 | 07-Как-жить-без-денег |
| 08 | 08-Не-подставляйтесь |
| 09 | 09-Юридические-красные-линии |
| 10 | 10-Окупается-ли-брак |
| 11 | 11-Красные-линии-для-технарей |
| 12 | 12-Своё-дело |
| 13 | 13-Экстренные-случаи |
| 14 | 14-Аккаунты-и-безопасность |
| 15 | 15-Аренда-и-покупка-жилья |
| 16 | 16-Жизнь-с-хронической-болезнью |
| 17 | 17-Пожилые-в-семье |
| 18 | 18-Окупаются-ли-дети |
| 19 | 19-Работа-и-травмы |
| 20 | 20-Новорождённый |
| 21 | 21-Заграница-и-безопасность |
| 22 | 22-Отдых-и-снятие-стресса |
| 23 | 23-Какую-профессию-учить |
| 24 | 24-У-врача |
| 25 | 25-После-смерти-человека |
| 26 | 26-Сайт-или-платформа |
| 27 | 27-Беременность-и-роды |
| 28 | 28-Не-ломайте-здоровье-ради-внешности |
| 29 | 29-После-тяжёлого-удара |
| 30 | 30-Ребёнок-в-школе |
| 31 | 31-Дороги-после-восемнадцати |
| 32 | 32-Учёба-за-границей |
| 33 | 33-Как-жить-после-инвалидности |
| 34 | 34-Домашние-лекарства-не-навреди |

README policy (decided 2026-09-18; clarified 2026-09-22): in the dlgrv fork the primary README language is **English**.
- `README.md` — English (GitHub root face + site default)
- `README.zh.md` — Chinese mirror of upstream `README.md` (see [docs/pipeline/upstream-sync.md](docs/pipeline/upstream-sync.md); never overwrite root `README.md` from upstream)
- `README.ru.md` — Russian translation
- `README.es.md` / `README.pt.md` — Spanish / Brazilian Portuguese
- Any further locale: `README.<lang>.md` + `book/<lang>/` (see [docs/pipeline/add-language.md](docs/pipeline/add-language.md))
Keep all READMEs linked via a `Languages:` line. Upstream sync ritual: [docs/pipeline/upstream-sync.md](docs/pipeline/upstream-sync.md).

EN filenames: English slugs under `book/en/`, same two-digit prefix (decided 2026-09-18):

| Ch | Slug |
|---|---|
| 01 | 01-Do-Not-Die-Early |
| 02 | 02-Do-Not-Die-Slowly |
| 03 | 03-Do-Not-Waste-Energy |
| 04 | 04-Do-Not-Waste-Time |
| 05 | 05-Do-Not-Waste-Money |
| 06 | 06-The-Anti-List |
| 07 | 07-Living-With-No-Money |
| 08 | 08-Do-Not-End-Up-Inside |
| 09 | 09-Legal-Red-Lines |
| 10 | 10-Is-Love-And-Marriage-Worth-It |
| 11 | 11-Red-Lines-For-Techies |
| 12 | 12-Starting-Your-Own-Business |
| 13 | 13-Emergencies |
| 14 | 14-Accounts-And-Security |
| 15 | 15-Renting-And-Buying-Housing |
| 16 | 16-Living-With-Chronic-Disease |
| 17 | 17-Elderly-At-Home |
| 18 | 18-Is-Having-Kids-Worth-It |
| 19 | 19-Employment-And-Work-Injury |
| 20 | 20-Newborn |
| 21 | 21-Travel-And-Abroad-Safety |
| 22 | 22-How-To-Relax |
| 23 | 23-Which-Skills-To-Learn |
| 24 | 24-Seeing-The-Doctor |
| 25 | 25-After-Someone-Dies |
| 26 | 26-Building-A-Website-Or-Platform |
| 27 | 27-Pregnancy-And-Birth |
| 28 | 28-Do-Not-Ruin-Health-For-Looks |
| 29 | 29-After-A-Major-Blow |
| 30 | 30-School-Age-Kids |
| 31 | 31-Paths-After-Eighteen |
| 32 | 32-Studying-Abroad |
| 33 | 33-Living-With-Disability |
| 34 | 34-Avoid-Serious-Harm-From-Home-Medicines |

## Russian README (README.ru.md)

- Root `README.md` is **English** (fork primary). Chinese TOC lives in `README.zh.md`.
- `README.ru.md` = full Russian translation of the guide front matter / TOC. Status line points at the Chinese original chapter set / `README.zh.md` where appropriate.
- All numbers byte-faithful to the Chinese abs values (locale comma/space OK). Citation lines stay byte-identical after the label.
- Badges: recreate with Russian labels (URL-encode programmatically), same colors/numbers,
  same link targets; anchors inside the doc point to translated headings.
- Chapter links → `book/ru/<Russian slug>.md`. Long-read links → `docs/ru/` when translated.
- Back-link in every `book/ru/` file: `[← К общему оглавлению](../../README.ru.md)`.

## Localization (RU) — no translated-English/epidemiology jargon

Goal: text must read like Russian popular science, not translated epidemiology.
Numbers, HR/RR/OR/CI values and CIs stay byte-identical — reword the words around them.

Rewrite in «Эффект» / «Примечания» body text (term may appear in parentheses once per file on first use):
- когорта / когортное исследование → «наблюдательное исследование N человек», «N человек под наблюдением», «объединённый анализ 15 наблюдательных исследований»
- экспозиция → «воздействие», «контакт с дымом/взвесью» (дома дыма больше, чем вне дома)
- верхний/нижний квартиль, квинтиль → «25% участников с самым высоким … против 25% с самым низким» (термин в скобках — не более 1 раза на файл)
- конфаундинг / остаточный конфаундинг → «смешивающие факторы», «часть смешивающих факторов остаётся неучтённой»
- популяция → «у японцев», «в японской выборке»
- низкодостоверные доказательства (GRADE) → «доказательства низкого качества»
- инцидент (бытовое значение) → «разовый случай», «происшествие»

Keep — established Russian scientific usage: метаанализ, рандомизированное испытание,
наблюдательное исследование, медиана наблюдения, доверительный интервал, отношение
рисков/шансов, исследование «случай–контроль»; «человеко-лет» keep with a short gloss
once per file («сумма лет наблюдения по всем участникам»).

«Простыми словами» stays strictly colloquial — none of the terms above (existing rule).

## Tone
Match the original: restrained, no exclamation marks, no moralizing, verb-first item titles. Grade A/B/C letters stay A/B/C.

## China-context disclaimer
Chapters 8, 9, 11, 15, 19, 25, 26, 31 (and any other chapter citing Chinese law) get one extra line under the heading:
"Chapter X cites Chinese laws and institutions; for readers outside China it is reference material, not applicable law." (RU equivalent.)

## Numbers (all locales) — verify / repair

Canonical abs values come from CN via `norm_numbers`. Locale spelling:

| Lang | Decimal | Thousands | Pitfall |
|---|---|---|---|
| EN | `.` | `,` or thin space | — |
| RU / ES / PT | `,` | space (ES/PT also `.`) | bare `0.499` → folds to `499`; write `0,499` |
| any | — | — | never `2022 523` as a bare dump (folds to `2022523`); pipeline uses `〔2022〕〔523〕` |

Do not ask the MT model to “fix numbers” in a retry loop — use `make repair` (mechanical).

## Spanish (ES) — conventions

Applies to `book/es/` and `docs/es/`. Status, keep-untouched, tone and
China-context rules above are identical; field labels are in the table above.

### ES file naming

`NN-Title-Slug.md`, Spanish Title-Case, e.g. `01-No-Mueras-Temprano.md`
(final slugs recorded in README.es.md table of contents; the table links
`book/es/NN-…`). Chapters **01–34** under `book/es/`.

### ES style

- Neutral international Spanish (es-419-compatible), no regional slang, no exclamation marks
- Live prose, not calque; no HR/RR/OR/CI/queue jargon inside `En términos sencillos`
- Chinese legal/medical identifiers keep hanzi + short Spanish gloss on first use: `《民法典》 (Código Civil)`
- Emergency numbers keep Chinese values in place; Spanish/RU/US equivalents only as a Notas gloss
- Sources are never translated (injected byte-for-byte)
- Dispute marker in Notas: starts with `En disputa`; TODO: `por verificar` (web UI badges)

## Portuguese (PT) — conventions

Applies to `book/pt/` and `README.pt.md` (pt-BR). Field labels in the table above
(`Custo` / `Em linguagem simples` / `Benefício` / `Nível de evidência` / `Fontes` / `Notas`).
Same number rules as ES. Chapters **01–34** under `book/pt/`; slugs as in TOC.
