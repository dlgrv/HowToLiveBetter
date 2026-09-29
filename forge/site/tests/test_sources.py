"""Regression tests for forge.site.sources (twin of site/index.html splitSources)."""

from __future__ import annotations

from forge.site.sources import split_sources, src_count

# Paracetamol-style citation: ASCII ; inside one author block, ； between sources.
PARACETAMOL = (
    "Larson AM, Polson J, Fontana RJ, et al.; Acute Liver Failure Study Group (2005). "
    "Acetaminophen-induced acute liver failure. Hepatology. "
    "<https://doi.org/10.1002/hep.20948>"
    "；国家药监局关于修订对乙酰氨基酚说明书的公告. "
    "<http://mpa.hunan.gov.cn/example.html>"
    "；21 CFR 201.326(a)(1)(iii)(A) Liver warning. "
    "<https://www.ecfr.gov/current/title-21/section-201.326>"
)


def test_paracetamol_et_al_semicolon():
    parts = split_sources(PARACETAMOL)
    assert len(parts) == 3
    assert src_count(PARACETAMOL) == 3
    assert "et al.; Acute Liver Failure Study Group" in parts[0]
    assert "https://doi.org/10.1002/hep.20948" in parts[0]
    assert "mpa.hunan.gov.cn" in parts[1]
    assert "ecfr.gov" in parts[2]


def test_single_url_with_internal_fullwidth_semicolons():
    s = "《中华人民共和国保险法》第二十八条、第三十四条；<https://www.gov.cn/example.html>"
    parts = split_sources(s)
    assert len(parts) == 1
    assert src_count(s) == 1
    assert "第二十八条" in parts[0]


def test_three_sources_fullwidth_separators():
    s = (
        "Author A (2020). Title A. <https://example.com/a>"
        "；Author B (2021). Title B. <https://example.com/b>"
        "；Author C (2022). Title C. <https://example.com/c>"
    )
    assert src_count(s) == 3
    assert len(split_sources(s)) == 3


def test_no_urls_ascii_semicolon_stays_one():
    s = "Smith et al.; Study Group (2005). Unpublished notes without a link"
    parts = split_sources(s)
    assert parts == [s]
    assert src_count(s) == 1


def test_no_urls_fullwidth_split():
    s = "第一条说明；第二条说明"
    assert split_sources(s) == ["第一条说明", "第二条说明"]
    assert src_count(s) == 2
