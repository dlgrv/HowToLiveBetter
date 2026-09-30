$-- Pandoc typst template. Body helpers follow `pandoc -D typst`. --$
#set terms(hanging-indent: 1.5em)

#set table(inset: 6pt, stroke: none)
#show table.cell: it => align(left, it)

#let horizontalRule = line(start: (25%, 0%), end: (75%, 0%))
#let divider = if "divider" in std { divider } else { horizontalRule }

#show figure.where(kind: table): set figure.caption(position: top)
#show figure.where(kind: image): set figure.caption(position: bottom)
#show figure: set block(breakable: true)
#set smartquote(enabled: false)

#set document(title: "$booktitle$", author: "dlgrv")
#set text(
  font: ("Libertinus Serif", "Noto Serif CJK SC", "Noto Serif SC", "Source Han Serif SC", "Noto Sans CJK SC", "Microsoft YaHei", "SimSun"),
  size: 10.5pt,
  lang: "$ebooklang$",
  region: "$ebookregion$",
)
#set par(justify: false, leading: 0.78em, spacing: 0.9em)
#set list(indent: 0.6em, spacing: 0.75em)
#show raw: set text(font: ("DejaVu Sans Mono", "Noto Sans Mono CJK SC", "Consolas"), size: 9pt)
#show link: set text(fill: rgb("#1a4fb4"))
#show heading: set block(sticky: true, above: 1.5em, below: 0.65em)
#show heading.where(level: 1): set text(19pt)
#show heading.where(level: 2): set text(14pt)
#show heading.where(level: 3): set text(11.5pt)
#show heading.where(level: 1): it => { pagebreak(weak: true); it }

#let running-head = context {
  let next = query(selector(heading.where(level: 1)).after(here())).at(0, default: none)
  if next != none and next.location().page() == here().page() { return }
  let seen = query(selector(heading.where(level: 1)).before(here()))
  if seen.len() == 0 { return }
  set text(8.5pt, fill: luma(120))
  grid(columns: (1fr, auto), align(left)[$booktitle$], align(right)[#seen.last().body])
  v(-7pt)
  line(length: 100%, stroke: 0.4pt + luma(215))
}

#set page(paper: "a4", margin: (x: 2.2cm, top: 2.2cm, bottom: 2cm), header: none, footer: none)
#align(center + horizon)[
  #image("$cover$", width: 100%)
  #v(1.6cm)
  #text(10pt, fill: luma(90))[
    $coverline1$ \
    $coverline2$ \
    $coverline3$
  ]
]

#pagebreak()
#outline(title: [$outlinetitle$], depth: 1, indent: 1em)

#pagebreak(weak: true)
#set page(header: running-head, footer: context align(center, text(8.5pt, fill: luma(120))[#counter(page).at(here()).first() / #counter(page).final().first()]))
#counter(page).update(1)

$body$
