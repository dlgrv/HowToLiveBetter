"""Sitemap generator over a staged publish tree."""

from forge.site import build_sitemap


def _make_publish(tmp_path):
    pub = tmp_path / ".publish"
    (pub / "en").mkdir(parents=True)
    (pub / "ru").mkdir()
    (pub / "book" / "en").mkdir(parents=True)
    (pub / "assets" / "og").mkdir(parents=True)
    (pub / "login").mkdir()
    (pub / "docs" / "research" / "en").mkdir(parents=True)
    (pub / "index.html").write_text("<html></html>")
    (pub / "en" / "index.html").write_text("<html lang='en'></html>")
    (pub / "README.md").write_text("# Book")
    (pub / "README.ru.md").write_text("# Книга")
    (pub / "book" / "01-die.md").write_text("# zh ch1")
    (pub / "book" / "en" / "01-die.md").write_text("# en ch1")
    (pub / "docs" / "research" / "en" / "guide.md").write_text("# research")
    # excluded noise
    (pub / "robots.txt").write_text("User-agent: *")
    (pub / "llms.txt").write_text("# map")
    (pub / "sitemap.xml").write_text("<old/>")
    (pub / "assets" / "v2.css").write_text("body{}")
    (pub / "assets" / "og" / "en.png").write_bytes(b"png")
    (pub / "login" / "index.html").write_text("<form>")
    (pub / "misc.html").write_text("<p>not indexed</p>")
    return pub


def test_collect_urls_covers_content_and_excludes_noise(tmp_path):
    pub = _make_publish(tmp_path)
    entries = build_sitemap.collect_urls(str(pub), str(tmp_path), ["en", "ru"])
    locs = [e["loc"] for e in entries]

    assert "https://book.dlgrv.com/" in locs
    assert "https://book.dlgrv.com/en/" in locs
    assert "https://book.dlgrv.com/README.md" in locs
    assert "https://book.dlgrv.com/README.ru.md" in locs
    assert "https://book.dlgrv.com/book/01-die.md" in locs
    assert "https://book.dlgrv.com/book/en/01-die.md" in locs
    assert "https://book.dlgrv.com/docs/research/en/guide.md" in locs

    # excluded: assets, login, meta files, non-hub html
    assert not any("/assets/" in u for u in locs)
    assert not any("/login" in u for u in locs)
    assert "https://book.dlgrv.com/robots.txt" not in locs
    assert "https://book.dlgrv.com/llms.txt" not in locs
    assert "https://book.dlgrv.com/sitemap.xml" not in locs
    assert "https://book.dlgrv.com/misc.html" not in locs


def test_priorities_by_url_kind(tmp_path):
    pub = _make_publish(tmp_path)
    by_loc = {
        e["loc"]: e["priority"]
        for e in build_sitemap.collect_urls(str(pub), str(tmp_path), ["en", "ru"])
    }
    assert by_loc["https://book.dlgrv.com/"] == "1.0"
    assert by_loc["https://book.dlgrv.com/en/"] == "0.9"
    assert by_loc["https://book.dlgrv.com/README.md"] == "0.8"
    assert by_loc["https://book.dlgrv.com/book/01-die.md"] == "0.7"
    assert by_loc["https://book.dlgrv.com/docs/research/en/guide.md"] == "0.3"


def test_render_is_valid_xml_and_sorted(tmp_path):
    pub = _make_publish(tmp_path)
    entries = build_sitemap.collect_urls(str(pub), str(tmp_path), ["en", "ru"])
    xml_text = build_sitemap.render_sitemap(entries)

    # well-formed by construction: declaration, one root, matched per-entry tags
    lines = xml_text.splitlines()
    assert lines[0] == '<?xml version="1.0" encoding="UTF-8"?>'
    assert lines[1] == '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    assert lines[-1] == "</urlset>"
    locs = [ln.strip()[len("<loc>") : -len("</loc>")] for ln in lines if "<loc>" in ln]
    assert locs == sorted(locs)
    assert len(locs) == len(entries)
    assert xml_text.count("<url>") == len(entries) == xml_text.count("</url>")
