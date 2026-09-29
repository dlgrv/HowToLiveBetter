# Forge — site, OG, repo gates

Repo-facing tooling that is **not** the translation conveyor.

| Path | Role |
|---|---|
| `forge/site/` | Pages builders (`build_pages`, `pages_artifact`) — **not** repo `site/` UI |
| `forge/og/` | OG HTML templates + `build_og_html.py` |
| `forge/v2.css` | skin source copied into `site/assets/` |
| `forge/ops/` | `check_content`, `check_links`, `check_commit_msg`, `update_readme`, `strip_zh_readme_ads` |

Translation publish path lives under [`translate/`](../translate/README.md).

```bash
make web-build    # forge/site/build_pages.py
make og           # forge/og → site/assets/og/
make check-content
make check-links
```
