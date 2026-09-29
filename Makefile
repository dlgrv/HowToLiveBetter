# HowToLiveBetter translation pipeline
# All commands run from repo root.
# Raw `python3 tools/…` needs PYTHONPATH=. (or use these targets).

export PYTHONPATH := $(CURDIR)

PY = .venv/bin/python3
RUFF = .venv/bin/ruff
DJLINT = .venv/bin/djlint
YAMLLINT = .venv/bin/yamllint

.PHONY: help sync-upstream digest assemble verify verify-all wave status lint format test test-integration ci og og-html update-readme hooks check-commit-msg pages-artifact serve web-build quality factcheck style check-content check-links

OG_HTML = tools/og/en.html tools/og/ru.html tools/og/es.html tools/og/zh.html

check-content:  ## CJK-leak, parity, readme-badge checks
	$(PY) tools/check_content.py

ci:  ## Local CI ≈ GitHub test job (tests+lint+links+content+pages+artifact)
	@echo "=== Running tests ==="
	$(PY) -m pytest tools/validate/tests/ tools/llm/tests/ -v --ignore=tools/validate/tests/integration
	@echo "=== Integration tests ==="
	$(PY) -m pytest tools/validate/tests/integration/ -v
	@echo "=== Lint ==="
	$(MAKE) lint
	@echo "=== Links ==="
	$(PY) tools/check_links.py
	@echo "=== Content ==="
	$(PY) tools/check_content.py
	@echo "=== Build pages ==="
	$(PY) tools/build_pages.py
	@test -f site/en/index.html && test -f site/assets/v2.css
	@test -f site/assets/og/en.png
	@echo "=== Pages artifact ==="
	$(PY) tools/pages_artifact.py
	@test -f .publish/en/index.html && test -f .publish/README.md && test -d .publish/book

hooks:  ## Install local git hooks (commit-msg + pre-commit lint/content + pre-push tests)
	git config core.hooksPath .githooks
	@echo "✓ core.hooksPath=.githooks (commit-msg, pre-commit lint+content, pre-push test+content)"

check-commit-msg:  ## Validate a message: make check-commit-msg MSG='fix: …'
	@[ -n "$(MSG)" ] || (echo "Usage: make check-commit-msg MSG='type: description'" && exit 1)
	@printf '%s\n' "$(MSG)" | $(PY) tools/check_commit_msg.py --stdin

# LANG from the environment is the locale (e.g. C.UTF-8); only honor command-line LANG=.
ifeq ($(origin LANG),command line)
QUALITY_LANGS := $(LANG)
else
QUALITY_LANGS := $(shell $(PY) -c 'from tools.pipeline.config import translation_langs; print(" ".join(translation_langs()))')
endif

quality:  ## Content quality (readability + style --book). Usage: make quality [LANG=ru]
	@for lang in $(QUALITY_LANGS); do \
		echo "=== $$lang: readability ==="; \
		$(PY) tools/readability.py $$lang --strict || exit 1; \
		echo "=== $$lang: style --book ==="; \
		$(PY) tools/style_check.py --book --lang $$lang --strict || exit 1; \
	done

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ── Upstream sync ──────────────────────────────────────────────

sync-upstream:  ## Fetch upstream CN changes (follow AGENTS.md ritual)
	@echo "→ Follow docs/pipeline/upstream-sync.md"
	git fetch upstream
	git checkout upstream/main -- $$(git ls-tree -r --name-only upstream/main book | grep -E '^book/[0-9]{2}-.*\.md$$')
	git checkout upstream/main -- $$(git ls-tree -r --name-only upstream/main docs | grep -E '^docs/[^/]+\.md$$' ; git ls-tree -r --name-only upstream/main docs/核实记录)
	git show upstream/main:README.md > README.zh.md
	$(PY) tools/strip_zh_readme_ads.py README.zh.md
	$(PY) tools/check_content.py
	@echo "→ Done. Review changes: git diff -- book/ README.zh.md"
	@echo "→ Never checkout ads/, site/, or tools/ from upstream"

# Zero-pad CH when set on the command line (locale LANG is unrelated).
ifeq ($(origin CH),command line)
CH_PAD := $(shell printf '%02d' $(CH))
else
CH_PAD :=
endif

# ── Digest ─────────────────────────────────────────────────────

digest:  ## Split CN chapter into units. Usage: make digest CH=01
	@[ -n "$(CH)" ] || (echo "Usage: make digest CH=NN" && exit 1)
	$(PY) tools/make_digest.py $(CH_PAD)

# ── Assemble ───────────────────────────────────────────────────

# Canonical wave workdir; override for smoke/other runs: WORKDIR=tools/runs/smoke/ru/01
WORKDIR ?= tools/runs/active/$(LANG)/$(CH_PAD)

assemble:  ## Assemble units → book chapter. Usage: make assemble CH=02 LANG=ru [WORKDIR=…]
	@[ -n "$(CH)" ] || (echo "Usage: make assemble CH=NN LANG=ru|en|es [WORKDIR=tools/runs/active/LANG/NN]" && exit 1)
	@[ -n "$(LANG)" ] || (echo "Usage: make assemble CH=NN LANG=ru|en|es [WORKDIR=…]" && exit 1)
	$(PY) tools/assemble.py $(CH_PAD) $(WORKDIR) book/$(LANG)/$(shell ls book/$(LANG)/ | grep "^$(CH_PAD)-") $(LANG)

# ── Verify ─────────────────────────────────────────────────────

verify:  ## Verify one translated chapter. Usage: make verify CH=01 LANG=ru
	@[ -n "$(CH)" ] || (echo "Usage: make verify CH=NN LANG=ru|en|es" && exit 1)
	@[ -n "$(LANG)" ] || (echo "Usage: make verify CH=NN LANG=ru|en|es" && exit 1)
	$(PY) tools/verify.py $(CH_PAD) --lang $(LANG) --json

verify-all:  ## Verify all chapters for a language. Usage: make verify-all LANG=ru
	@[ -n "$(LANG)" ] || (echo "Usage: make verify-all LANG=ru|en|es" && exit 1)
	@for ch in $$(ls book/$(LANG)/ | grep -oE '^[0-9]+' | sort -n | uniq); do \
		nn=$$(printf '%02d' $$ch); \
		echo "=== Chapter $$nn ($(LANG)) ==="; \
		$(PY) tools/verify.py $$nn --lang $(LANG) --json; \
	done

# ── Wave pipeline ───────────────────────────────────────────────

wave:  ## Run assemble+verify for a wave. Usage: make wave WAVE=1
	@[ -n "$(WAVE)" ] || (echo "Usage: make wave WAVE=N" && exit 1)
	@$(PY) -c "import json; w=json.load(open('waves.json')); print('Wave $(WAVE):', w['waves']['$(WAVE)']['chapters'])"
	@$(PY) tools/wave_pipeline.py $$($(PY) -c "import json; print(' '.join(f'{int(c):02d}' for c in json.load(open('waves.json'))['waves']['$(WAVE)']['chapters']))")

# ── Status ─────────────────────────────────────────────────────

status:  ## Show translation dashboard
	$(PY) tools/status.py

update-readme:  ## Audit README/OG. Usage: make update-readme [ARGS=--fix]
	$(PY) tools/update_readme.py $(ARGS)

# ── Web ────────────────────────────────────────────────────────

web-build:  ## Regenerate site/{lang}/ pages from site/index.html
	$(PY) tools/build_pages.py

og-html:  ## Render tools/og/{en,ru,es,zh}.html from _template.html
	$(PY) tools/og/build_og_html.py

og: og-html  ## Regenerate OG PNGs from tools/og/*.html → site/assets/og/
	@mkdir -p site/assets/og
	@for lang in en ru es zh; do \
		"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
			--headless --disable-gpu --hide-scrollbars \
			--force-device-scale-factor=1 --window-size=1200,630 \
			--screenshot=site/assets/og/$$lang.png tools/og/$$lang.html; \
		echo "✓ site/assets/og/$$lang.png"; \
	done

pages-artifact: web-build  ## Stage flat Pages tree in .publish/ (site + book + README*)
	$(PY) tools/pages_artifact.py

serve: pages-artifact  ## Local preview of the Pages artifact on :8000
	@echo "→ http://127.0.0.1:8000/en/"
	cd .publish && $(PY) -m http.server 8000

# ── Quality ────────────────────────────────────────────────────

format:  ## Auto-fix Python tools + OG HTML
	$(RUFF) format tools/
	$(RUFF) check --fix tools/
	# djlint --reformat: 0=unchanged, 1=rewrote; other codes are real failures
	@status=0; $(DJLINT) $(OG_HTML) --reformat || status=$$?; \
		if [ $$status -ne 0 ] && [ $$status -ne 1 ]; then exit $$status; fi
	$(DJLINT) $(OG_HTML) --check

lint:  ## All code linters (must match CI)
	$(RUFF) format --check tools/
	$(RUFF) check tools/
	$(DJLINT) $(OG_HTML) --check
	$(DJLINT) site/index.html --lint
	$(YAMLLINT) .github/workflows/
	shellcheck tools/llm/*.sh tools/laya/*.sh

test:  ## Run unit tests (excludes integration)
	$(PY) -m pytest tools/validate/tests/ tools/llm/tests/ tools/laya/tests/ -v --ignore=tools/validate/tests/integration

test-integration:  ## Run integration tests (golden manifests, E2E)
	$(PY) -m pytest tools/validate/tests/integration/ -v

factcheck:  ## Unit fact-check. Usage: make factcheck CH=01 LANG=ru|en CN=… TR=…
	@[ -n "$(CH)" ] && [ -n "$(LANG)" ] && [ -n "$(CN)" ] && [ -n "$(TR)" ] || \
		(echo "Usage: make factcheck CH=NN LANG=ru|en CN=path/to/cn.md TR=path/to/tr.md" && exit 1)
	$(PY) tools/validate/factcheck.py --chapter $(CH_PAD) --lang $(LANG) --cn-unit $(CN) --tr-unit $(TR)

style:  ## Style audit (WARN-only). Usage: make style CH=10 LANG=ru
	@[ -n "$(CH)" ] && [ -n "$(LANG)" ] || (echo "Usage: make style CH=NN LANG=ru|en|es" && exit 1)
	$(PY) tools/style_check.py book/$(LANG)/$(shell ls book/$(LANG)/ | grep "^$(CH_PAD)-") --lang $(LANG)

# ── Links ──────────────────────────────────────────────────────

check-links:  ## Validate all relative links in book/ and docs/
	$(PY) tools/check_links.py
