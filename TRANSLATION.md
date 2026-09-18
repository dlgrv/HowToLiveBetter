# Translation conventions (EN / RU)

Applies to everything under `book/en/` and `book/ru/`.

## Status line
First line of every translated file, before the back-link:

```
> Unofficial translation of [book/01-不要早死.md](../01-不要早死.md). In case of any discrepancy the Chinese original prevails.
```
(RU: «Неофициальный перевод файла book/01-….md. При расхождениях приоритет у китайского оригинала.»)

## Keep untouched
- Full citation lines in `- 来源：/来源` — author names, journal names, DOIs, URLs, Chinese regulation titles + document numbers stay exactly as in the original. Only the surrounding field label is translated.
- All numbers, HR/RR/OR/CI values, percentages, prices.
- The HTML cost-tag comment `<!-- 成本标签: ... -->` — keep the Chinese field names (钱/时间/毅力/收益/口径) and values byte-identical; index.html parses it.
- Markdown structure: heading levels, `### N.` numbering, list-item order, links.

## Translate
- Field labels: 成本→Cost/Стоимость, 说人话→In plain terms/Простыми словами, 收益→Benefit/Эффект, 证据等级→Evidence grade/Уровень доказательности, 来源→Sources/Источники, 备注→Notes/Примечания.
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

README policy (decided 2026-09-18): in the dlgrv fork the primary README language is English.
- `README.md` — English (becomes the root README on `translation/en` and fork `main`)
- `README.zh.md` — Chinese (renamed copy of the original Chinese README, links back to EN + RU)
- `README.ru.md` — Russian (existing; gets a tri-lingual Languages line)
Apply when the EN README is ready; keep all three linked via a `Languages:` line.

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

## Russian README (README.ru.md)

- `README.md` (Chinese) stays byte-identical — `index.html` reads it, upstream owns it.
  Only addition allowed: one «Языки / Languages» selector line in the header.
- `README.ru.md` = full Russian translation of `README.md`. First line: status
  («> Неофициальный перевод файла [README.md](README.md). При расхождениях приоритет у китайского оригинала.»)
  + link back to the Chinese README.
- All numbers byte-faithful (528, 347/131/50, 88/248/162, 97.2%, thresholds…). The
  example item block keeps citation lines byte-identical after the label.
- Badges: recreate with Russian labels (URL-encode programmatically), same colors/numbers,
  same link targets; anchors inside the doc point to translated headings.
- Chapter links → `book/ru/<Russian slug>.md`. `docs/*` links keep Chinese targets
  (not translated yet), label = Russian title + «(на китайском)».
- Back-link in every `book/ru/` file: `[← К общему оглавлению](../../README.ru.md)`
  (replaces the earlier `../../README.md` rule).

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
