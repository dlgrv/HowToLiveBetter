$-- Pandoc typst template. Body helpers follow `pandoc -D typst`. --$
// Vertical rhythm (print BP: Butterick + Bringhurst):
// - one body leading (~130% size); add/remove space in related steps
// - paragraph OR indent, not both → we use paragraph gap
// - para gap ≈ leading + 4–10pt (Butterick); headings: more above than below
// - fields / TOC / lists ≥ leading so block breaks never read tighter than lines
#let lead = 0.65em
#let para-gap = lead + 6pt
#let field-gap = lead + 5pt
#let list-gap = lead + 4pt
#let toc-gap = lead + 5pt
#let head-above = 1.5em
#let head-below = 0.7em

#set terms(hanging-indent: 1.5em)
#show terms.item: it => {
  block(breakable: true, spacing: field-gap, {
    strong(it.term)
    [. ]
    it.description
  })
}

#set table(inset: (x: 5pt, y: 4pt), stroke: 0.4pt + luma(170))
#show table.cell: it => {
  show regex("[A-Za-z0-9./:?#&=%_~+-]{24,}"): piece => {
    let chars = piece.text.clusters()
    let out = ()
    for (i, c) in chars.enumerate() {
      out.push(c)
      if calc.rem(i + 1, 12) == 0 and i + 1 < chars.len() {
        out.push(sym.zws)
      }
    }
    out.join()
  }
  align(left, it)
}

#let horizontalRule = line(start: (25%, 0%), end: (75%, 0%))
#let divider = horizontalRule

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
#set par(justify: false, leading: lead, spacing: para-gap)
#set list(indent: 0.6em, spacing: list-gap)
#show raw: set text(font: ("DejaVu Sans Mono", "Noto Sans Mono CJK SC", "Consolas"), size: 9pt)
#show link: set text(fill: rgb("#1a4fb4"))
#show heading: set block(sticky: true, above: head-above, below: head-below)
#show heading.where(level: 1): set text(19pt)
#show heading.where(level: 2): set text(14pt)
#show heading.where(level: 3): set text(11.5pt)
#show heading.where(level: 1): it => { pagebreak(weak: true); it }
#show outline.entry: set block(spacing: toc-gap)

#let running-head = context {
  let next = query(selector(heading.where(level: 1)).after(here())).at(0, default: none)
  if next != none and next.location().page() == here().page() { return }
  let seen = query(selector(heading.where(level: 1)).before(here()))
  if seen.len() == 0 { return }
  set text(8.5pt, fill: luma(120))
  grid(columns: (1fr, auto), align(left)[$booktitle$], align(right)[#seen.last().body])
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
#show link: it => underline(stroke: 0.45pt + rgb("#1a4fb4"), offset: 1.5pt, text(fill: rgb("#1a4fb4"), it))
#set page(header: running-head, footer: context align(center, text(8.5pt, fill: luma(120))[#counter(page).at(here()).first() / #counter(page).final().first()]))
#counter(page).update(1)

$body$
