"""updates.json generator: item diff, git walker, writer."""

import json
import subprocess

import pytest

from forge.site import build_updates

CH1_V1 = """# 01. Не умирай рано

### 1. Первый пункт
- 成本： бесплатно
- 说人话： просто
- 收益： много
- 证据等级： A
- 来源： <https://a.example/1>
- 备注： заметка один

### 2. Второй пункт
- 成本： мало
- 说人话： коротко
- 收益： средне
- 证据等级： B
- 来源： <https://a.example/2>
"""

CH1_V2_NOTE_ONLY = CH1_V1.replace("заметка один", "заметка один (обновлена)")

CH1_V2_TITLE = CH1_V1.replace("### 2. Второй пункт", "### 2. Второй пункт (внятнее)")

CH1_V2_ADDED = (
    CH1_V1
    + """
### 3. Третий пункт
- 成本： ноль
"""
)

CH1_V2_REMOVED = CH1_V1.replace(
    """
### 2. Второй пункт
- 成本： мало
- 说人话： коротко
- 收益： средне
- 证据等级： B
- 来源： <https://a.example/2>
""",
    "",
)


def test_diff_items_field_change():
    d = build_updates.diff_items(CH1_V1, CH1_V2_NOTE_ONLY)
    assert d["added"] == []
    assert d["removed"] == []
    assert d["changed"] == [{"n": "1", "fields": ["notes"]}]


def test_diff_items_title_change_first():
    d = build_updates.diff_items(CH1_V1, CH1_V2_TITLE)
    assert d["changed"] == [{"n": "2", "fields": ["title"]}]


def test_diff_items_add_and_remove():
    d = build_updates.diff_items(CH1_V1, CH1_V2_ADDED)
    assert d["added"] == ["3"]
    assert d["removed"] == []

    d = build_updates.diff_items(CH1_V1, CH1_V2_REMOVED)
    assert d["added"] == []
    assert d["removed"] == ["2"]


def test_split_items_ignores_h2_sections():
    # '## N.' headings must not be captured as items; blocks run to the next heading.
    md = "# 01. T\n\n## 1. Intro\nтекст\n\n### 1. Один\n- 成本： 0\n\n### 2. Два\n"
    items = build_updates.split_items(md)
    assert list(items) == ["1", "2"]
    assert "- 成本： 0" in items["1"]


# ---------- git walker ----------


def _git(repo, *args):
    subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
        env={
            "PATH": "/usr/bin:/bin:/usr/local/bin",
            "HOME": str(repo),
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@example.com",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@example.com",
        },
    )


def _commit_all(repo, date):
    env = {
        "PATH": "/usr/bin:/bin:/usr/local/bin",
        "HOME": str(repo),
        "GIT_AUTHOR_DATE": date,
        "GIT_COMMITTER_DATE": date,
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.com",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.com",
    }
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True, env=env)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-m", "c"], check=True, capture_output=True, env=env
    )


@pytest.fixture
def git_repo(tmp_path):
    repo = tmp_path / "repo"
    (repo / "book").mkdir(parents=True)
    _git(repo, "init", "-q")
    return repo


def test_collect_history_full_walk(git_repo):
    v1 = git_repo / "book" / "01-test.md"
    v1.write_text(CH1_V1, encoding="utf-8")
    _commit_all(git_repo, "2026-01-01T10:00:00+00:00")

    v2 = (
        CH1_V1.replace("заметка один", "заметка один (обновлена)")
        + """
### 3. Третий пункт
- 成本： ноль
"""
    )
    v1.write_text(v2, encoding="utf-8")
    # 02 arrives after the import commit → its items are genuinely "added".
    (git_repo / "book" / "02-test.md").write_text(CH1_V1, encoding="utf-8")
    _commit_all(git_repo, "2026-01-05T10:00:00+00:00")

    hist = build_updates.collect_history(str(git_repo))

    # ch01 was part of the import commit: baseline, no "added" flags.
    assert hist["01-1"] == {"changed": "2026-01-05", "fields": ["notes"]}
    assert "01-2" not in hist  # baseline, unchanged → no record
    assert hist["01-3"] == {"added": "2026-01-05"}
    # ch02 first appeared after the import.
    assert hist["02-1"] == {"added": "2026-01-05"}
    assert hist["02-2"] == {"added": "2026-01-05"}


def test_collect_history_single_commit_is_baseline(git_repo):
    (git_repo / "book" / "02-test.md").write_text(CH1_V1, encoding="utf-8")
    _commit_all(git_repo, "2026-02-01T10:00:00+00:00")

    assert build_updates.collect_history(str(git_repo)) == {}


def test_collect_history_ignores_locale_dirs(git_repo):
    (git_repo / "book" / "en").mkdir()
    (git_repo / "book" / "en" / "01-test.md").write_text(CH1_V1, encoding="utf-8")
    _commit_all(git_repo, "2026-01-01T10:00:00+00:00")

    assert build_updates.collect_history(str(git_repo)) == {}


def test_write_updates_payload_and_order(tmp_path, monkeypatch):
    monkeypatch.setattr(
        build_updates,
        "collect_history",
        lambda _root: {"2-1": {"added": "2026-01-02"}, "1-10": {"added": "2026-01-01"}},
    )
    pub = tmp_path / ".publish"
    pub.mkdir()
    n = build_updates.write_updates(str(pub), str(tmp_path))
    assert n == 2
    data = json.loads((pub / "updates.json").read_text(encoding="utf-8"))
    assert list(data["items"]) == ["1-10", "2-1"]
    assert data["generated"]


def test_write_updates_survives_git_failure(tmp_path, monkeypatch):
    def boom(_root):
        raise RuntimeError("no git")

    monkeypatch.setattr(build_updates, "collect_history", boom)
    pub = tmp_path / ".publish"
    pub.mkdir()
    n = build_updates.write_updates(str(pub), str(tmp_path))
    assert n == 0
    data = json.loads((pub / "updates.json").read_text(encoding="utf-8"))
    assert data["items"] == {}


def test_git_raises_on_failed_command():
    # Real git, real exit code, real stderr — also proves capture_output/text work.
    with pytest.raises(RuntimeError, match="git"):
        build_updates._git(".", "log", "--bogus-flag")


def test_git_timeout_propagates(monkeypatch):
    def slow(*_args, **_kwargs):
        raise build_updates.subprocess.TimeoutExpired("git", 1)

    monkeypatch.setattr(build_updates.subprocess, "run", slow)
    with pytest.raises(build_updates.subprocess.TimeoutExpired):
        build_updates._git(".", "log")
