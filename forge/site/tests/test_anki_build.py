"""Anki .apkg builder integration: build via node, validate with python sqlite3.

The key invariant: stable GUIDs — rebuilding the deck must produce the same
guid set, so re-imports update existing cards instead of duplicating them.
"""

import json
import os
import re
import sqlite3
import subprocess
import tempfile
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
BUILD = ROOT / "forge/ebook/anki/build.mjs"


@pytest.fixture(scope="module")
def apkg_path():
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "deck.apkg"
        subprocess.run(
            ["node", str(BUILD), "--lang", "en", "--out", str(out)],
            cwd=ROOT,
            check=True,
            capture_output=True,
        )
        yield out


def _open_db(apkg: Path):
    zf = zipfile.ZipFile(apkg)
    assert zf.namelist() == ["collection.anki2", "media"]
    assert zf.read("media") == b"{}"
    with tempfile.NamedTemporaryFile(suffix=".anki2", delete=False) as fh:
        fh.write(zf.read("collection.anki2"))
        path = fh.name
    db = sqlite3.connect(path)
    return db, path


def test_apkg_structure_and_counts(apkg_path):
    db, path = _open_db(apkg_path)
    try:
        notes = db.execute("select count(*) from notes").fetchone()[0]
        cards = db.execute("select count(*) from cards").fetchone()[0]
        decks = json.loads(db.execute("select decks from col").fetchone()[0])
        models = json.loads(db.execute("select models from col").fetchone()[0])
        subdecks = [d["name"] for d in decks.values() if "::" in d["name"]]
        assert cards == notes
        # Notes == ### items actually present in the en chapters.
        item_count = 0
        for md in sorted((ROOT / "book/en").glob("*.md")):
            item_count += len(re.findall(r"^### ", md.read_text(encoding="utf-8"), re.MULTILINE))
        assert notes == item_count
        # One subdeck per chapter (34) + Default, one model, non-empty fields.
        assert len(subdecks) == 34
        assert all("HowToLiveBetter en::" in n for n in subdecks)
        assert len(models) == 1
        (mid,) = models.keys()
        assert all(r[0] == int(mid) for r in db.execute("select distinct mid from notes"))
        empty = db.execute("select count(*) from notes where flds = '' or flds is null").fetchone()[
            0
        ]
        assert empty == 0
    finally:
        db.close()
        os.unlink(path)


def test_apkg_guids_stable_across_rebuilds(apkg_path):
    db1, path1 = _open_db(apkg_path)
    guids1 = {r[0] for r in db1.execute("select guid from notes")}
    db1.close()
    os.unlink(path1)

    with tempfile.TemporaryDirectory() as td:
        out2 = Path(td) / "deck2.apkg"
        subprocess.run(
            ["node", str(BUILD), "--lang", "en", "--out", str(out2)],
            cwd=ROOT,
            check=True,
            capture_output=True,
        )
        db2, path2 = _open_db(out2)
        guids2 = {r[0] for r in db2.execute("select guid from notes")}
        db2.close()
        os.unlink(path2)

    assert guids1 == guids2
    assert len(guids1) > 700
