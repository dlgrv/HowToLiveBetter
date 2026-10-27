"""Python twin tests for the self-check scoring model."""

from forge.site.sc_model import sc_score, sc_top

E = [
    {"id": "1-1", "sec": "1", "n": "1", "ratio": "极高", "cs": 0},
    {"id": "1-2", "sec": "1", "n": "2", "ratio": "高", "cs": 2},
    {"id": "2-1", "sec": "2", "n": "1", "ratio": "一般", "cs": 1},
    {"id": "2-2", "sec": "2", "n": "2", "ratio": "极高", "cs": 4},
]


def test_score_counts_answered_only():
    ans = {"1-1": 1, "1-2": 0, "2-1": 0}
    got = sc_score(E, ans)
    assert got == [
        {"sec": "1", "total": 2, "yes": 1},
        {"sec": "2", "total": 1, "yes": 0},
    ]


def test_score_empty_when_no_answers():
    assert sc_score(E, {}) == []


def test_top_orders_ratio_then_cost():
    ans = {"1-1": 0, "1-2": 0, "2-1": 0, "2-2": 0}
    got = sc_top(E, ans)
    # 极高 with cs=0 first; then 极高 cs=4; then 高; then 一般.
    assert [e["id"] for e in got] == ["1-1", "2-2", "1-2", "2-1"]


def test_top_ignores_yes_and_unanswered():
    ans = {"1-1": 1, "2-2": 0}
    got = sc_top(E, ans)
    assert [e["id"] for e in got] == ["2-2"]


def test_top_caps_k():
    ans = {e["id"]: 0 for e in E}
    assert len(sc_top(E, ans, 2)) == 2


def test_top_survives_non_numeric_item_numbers():
    # The `n` field is data, not a promise: a non-numeric item sorts by the
    # numeric fallback (0), not crash; the weakest item stays last.
    entries = [*E, {"id": "1-x", "sec": "1", "n": "x", "ratio": "极高", "cs": 0}]
    ids = [e["id"] for e in sc_top(entries, {e["id"]: 0 for e in entries})]
    assert "1-x" in ids
    assert ids[-1] == "2-1"


def test_top_default_k_is_eight():
    # >8 unmet entries and no explicit k: exactly the default 8 come back.
    entries = [
        {"id": f"1-{i}", "sec": "1", "n": str(i), "ratio": "一般", "cs": i} for i in range(1, 10)
    ]
    got = sc_top(entries, {e["id"]: 0 for e in entries})
    assert [e["id"] for e in got] == [f"1-{i}" for i in range(1, 9)]
