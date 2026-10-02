"""Research notes linked from the book must survive Pages staging."""

from forge.site import pages_artifact


def test_stages_research_with_book_and_removes_stale_files(tmp_path, monkeypatch):
    site = tmp_path / "site"
    site.mkdir()
    (site / "index.html").write_text("<html></html>")
    book = tmp_path / "book" / "id"
    book.mkdir(parents=True)
    (book / "07-example.md").write_text("[Guide](../../docs/research/id/guide.md)")
    research = tmp_path / "docs" / "research" / "id"
    research.mkdir(parents=True)
    (research / "guide.md").write_text("# Indonesia")
    (tmp_path / "README.id.md").write_text("# Book")
    out = tmp_path / ".publish"
    out.mkdir()
    (out / "stale.md").write_text("stale")
    monkeypatch.setattr(pages_artifact, "ROOT", str(tmp_path))
    monkeypatch.setattr(pages_artifact, "SITE", str(site))
    monkeypatch.setattr(pages_artifact, "OUT", str(out))

    assert pages_artifact.main() == 0
    assert (out / "book/id/07-example.md").is_file()
    assert (out / "docs/research/id/guide.md").read_text() == "# Indonesia"
    assert (out / "README.id.md").is_file()
    assert not (out / "stale.md").exists()
