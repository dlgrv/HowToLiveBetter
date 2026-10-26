"""Python twin of the site updMatch() predicate (forge/site/upd_match.py)."""

from forge.site.upd_match import upd_match

NOW = 1_800_000_000_000  # fixed epoch ms


def test_changed_within_window():
    e = {"upd": {"changed": "2027-01-13"}}
    assert upd_match(e, {"changed"}, 30, NOW) is True


def test_changed_outside_window():
    e = {"upd": {"changed": "2027-01-01"}}
    assert upd_match(e, {"changed"}, 7, NOW) is False


def test_kind_selectivity():
    e = {"upd": {"added": "2027-01-01", "changed": "2027-01-13"}}
    assert upd_match(e, {"added"}, 7, NOW) is False
    assert upd_match(e, {"added", "changed"}, 7, NOW) is True


def test_missing_upd_or_kinds():
    assert upd_match({}, {"changed"}, 30, NOW) is False
    assert upd_match({"upd": {"changed": "2027-01-13"}}, set(), 30, NOW) is False
    assert upd_match({"upd": {}}, {"changed"}, 30, NOW) is False
