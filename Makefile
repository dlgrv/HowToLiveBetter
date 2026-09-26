# HowToLiveBetter translation pipeline
# All commands run from repo root.

.PHONY: help sync-upstream digest assemble verify verify-all wave status lint test

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ── Upstream sync ──────────────────────────────────────────────

sync-upstream:  ## Fetch upstream CN changes (follow AGENTS.md ritual)
	@echo "→ Follow docs/upstream-sync.md"
	git fetch upstream
	git checkout upstream/main -- $$(git ls-tree -r --name-only upstream/main book | grep -E '^book/[0-9]{2}-.*\.md$$')
	git checkout upstream/main -- $$(git ls-tree -r --name-only upstream/main docs | grep -E '^docs/[^/]+\.md$$' ; git ls-tree -r --name-only upstream/main docs/核实记录)
	git show upstream/main:README.md > README.zh.md
	python3 tools/check_content.py
	@echo "→ Done. Review changes: git diff -- book/ README.zh.md"

# ── Digest ─────────────────────────────────────────────────────

digest:  ## Split CN chapter into units. Usage: make digest CH=01
	@[ -n "$(CH)" ] || (echo "Usage: make digest CH=NN" && exit 1)
	python3 tools/make_digest.py $(CH)

# ── Assemble ───────────────────────────────────────────────────

assemble:  ## Assemble translated units into book chapter. Usage: make assemble CH=02 LANG=ru WORKDIR=run/ru/02
	@[ -n "$(CH)" ] || (echo "Usage: make assemble CH=NN LANG=ru|en|es WORKDIR=run/LANG/NN" && exit 1)
	@[ -n "$(LANG)" ] || (echo "Usage: make assemble CH=NN LANG=ru|en|es WORKDIR=..." && exit 1)
	@[ -n "$(WORKDIR)" ] || (echo "Usage: make assemble CH=NN LANG=ru|en|es WORKDIR=..." && exit 1)
	python3 tools/assemble.py $(CH) $(WORKDIR) book/$(LANG)/$(shell ls book/$(LANG)/ | grep "^$(CH)-")

# ── Verify ─────────────────────────────────────────────────────

verify:  ## Verify one translated chapter. Usage: make verify CH=01 LANG=ru
	@[ -n "$(CH)" ] || (echo "Usage: make verify CH=NN LANG=ru|en|es" && exit 1)
	@[ -n "$(LANG)" ] || (echo "Usage: make verify CH=NN LANG=ru|en|es" && exit 1)
	python3 tools/verify.py $(CH) --lang $(LANG) --json

verify-all:  ## Verify all chapters for a language. Usage: make verify-all LANG=ru
	@[ -n "$(LANG)" ] || (echo "Usage: make verify-all LANG=ru|en|es" && exit 1)
	@for ch in $$(ls book/$(LANG)/ | grep -oE '^[0-9]+' | sort -n | uniq); do \
		echo "=== Chapter $$ch ($(LANG)) ==="; \
		python3 tools/verify.py $$ch --lang $(LANG) --json || true; \
	done

# ── Wave pipeline ───────────────────────────────────────────────

wave:  ## Run assemble+verify for a wave. Usage: make wave WAVE=1
	@[ -n "$(WAVE)" ] || (echo "Usage: make wave WAVE=N" && exit 1)
	python3 -c "
import json
waves = json.load(open('waves.json'))
chapters = waves['waves']['$(WAVE)']['chapters']
print('Wave $(WAVE):', chapters)
" 
	python3 tools/wave_pipeline.py $$(python3 -c "import json; print(' '.join(map(str, json.load(open('waves.json'))['waves']['$(WAVE)']['chapters'])))")

# ── Status ─────────────────────────────────────────────────────

status:  ## Show translation dashboard
	python3 tools/status.py

# ── Web ────────────────────────────────────────────────────────

web-build:  ## Regenerate per-language and v1/v2 pages
	python3 tools/build_pages.py

# ── Quality ────────────────────────────────────────────────────

lint:  ## Lint Python tools
	ruff check tools/ --select E,F --ignore E501 2>/dev/null || echo "→ ruff not installed"

test:  ## Run all tests
	cd tools/validate && python3 -m pytest tests/ -v

factcheck:  ## Semantic fact-check against CN source. Usage: make factcheck CH=10 LANG=ru
	@[ -n "$(CH)" ] && [ -n "$(LANG)" ] || (echo "Usage: make factcheck CH=NN LANG=ru|en|es" && exit 1)
	python3 tools/validate/factcheck.py --chapter $(CH) --lang $(LANG)

style:  ## Style audit (WARN-only). Usage: make style CH=10 LANG=ru
	@[ -n "$(CH)" ] && [ -n "$(LANG)" ] || (echo "Usage: make style CH=NN LANG=ru|en|es" && exit 1)
	python3 tools/style_check.py $(CH) $(LANG)

# ── Links ──────────────────────────────────────────────────────

check-links:  ## Validate all relative links in book/ and docs/
	python3 tools/check_links.py