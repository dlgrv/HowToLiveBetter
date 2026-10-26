"""Python twin tests for the situation-chips predicate."""

from forge.site.sit_match import SITUATIONS, sit_match

E_CH16 = {"sec": "16", "money": "多", "time": "中", "will": "些"}
E_CH17 = {"sec": "17", "money": "0", "time": "少", "will": "否"}
E_CH01 = {"sec": "01", "money": "0", "time": "少", "will": "否"}


def test_age_tags():
    assert sit_match(E_CH16, {"60"}) is True
    assert sit_match(E_CH16, {"35"}) is True
    assert sit_match(E_CH17, {"60"}) is True
    assert sit_match(E_CH17, {"35"}) is False
    assert sit_match(E_CH01, {"60"}) is False
    assert sit_match(E_CH01, {"35"}) is False


def test_derived_tags():
    assert sit_match(E_CH01, {"free"}) is True
    assert sit_match({"sec": "01", "money": "少"}, {"free"}) is False
    assert sit_match(E_CH01, {"d30"}) is True
    assert sit_match({"sec": "01", "time": "少", "will": "是"}, {"d30"}) is False
    assert sit_match({"sec": "01", "time": "多", "will": "否"}, {"d30"}) is False


def test_or_across_tags_and_empty():
    assert sit_match(E_CH17, {"60", "d30"}) is True
    assert sit_match(E_CH16, {"free", "d30"}) is False
    assert sit_match(E_CH16, set()) is False


def test_age_lists_sorted_unique_and_two_digit():
    for chapters in SITUATIONS["age"].values():
        assert len(chapters) == len(set(chapters))
        assert all(len(c) == 2 and c.isdigit() for c in chapters)
