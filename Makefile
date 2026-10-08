# HowToLiveBetter translation pipeline
# All commands run from repo root.
# Raw `python3 translate/…` needs PYTHONPATH=. (or use these targets).

export PYTHONPATH := $(CURDIR)

PY = .venv/bin/python3
RUFF = .venv/bin/ruff
DJLINT = .venv/bin/djlint
YAMLLINT = .venv/bin/yamllint

.PHONY: help sync-upstream digest assemble verify verify-all wave repair status lint format test test-integration ci og og-html update-readme hooks check-commit-msg pages-artifact serve web-build quality style lt check-content check-links ebook-deps ebook-test ebook-epub ebook-pdf ebooks api-dev api-test api-lint api-format api-build api-smoke api-vuln api-cover

GOLANGCI_LINT_VERSION := v2.1.6
GOLANGCI_LINT := github.com/golangci/golangci-lint/v2/cmd/golangci-lint@$(GOLANGCI_LINT_VERSION)
API_DIR := api

# Locale list must stay in sync with translate/langs.json (registry).
OG_HTML = forge/og/en.html forge/og/ru.html forge/og/es.html forge/og/zh.html forge/og/pt.html forge/og/ar.html forge/og/id.html

check-content:  ## CJK-leak, parity, readme-badge checks
	$(PY) forge/ops/check_content.py

ci:  ## Local CI ≈ GitHub test job (tests+lint+links+content+pages+artifact)
	@echo "=== Running tests ==="
	$(PY) -m pytest translate/validate/tests/ translate/llm/tests/ forge/site/tests/ -v --ignore=translate/validate/tests/integration
	@echo "=== Integration tests ==="
	$(PY) -m pytest translate/validate/tests/integration/ -v
	@echo "=== Lint ==="
	$(MAKE) lint
	@echo "=== Links ==="
	$(PY) forge/ops/check_links.py
	@echo "=== Content ==="
	$(PY) forge/ops/check_content.py
	@echo "=== Build pages ==="
	$(PY) forge/site/build_pages.py
	@test -f site/en/index.html && test -f site/assets/v2.css
	@test -f site/assets/og/en.png
	@echo "=== Pages artifact ==="
	$(PY) forge/site/pages_artifact.py
	@test -f .publish/en/index.html && test -f .publish/README.md && test -d .publish/book
	@echo "=== API ==="
	$(MAKE) api-lint
	$(MAKE) api-test
	cd $(API_DIR) && CGO_ENABLED=0 go build -o /tmp/htlb-api-ci ./cmd/htlb-api

hooks:  ## Install local git hooks (commit-msg + pre-commit lint/content + pre-push tests)
	git config core.hooksPath .githooks
	@echo "✓ core.hooksPath=.githooks (commit-msg, pre-commit lint+content, pre-push test+content)"

check-commit-msg:  ## Validate a message: make check-commit-msg MSG='fix: …'
	@[ -n "$(MSG)" ] || (echo "Usage: make check-commit-msg MSG='type: description'" && exit 1)
	@printf '%s\n' "$(MSG)" | $(PY) forge/ops/check_commit_msg.py --stdin

# LANG from the environment is the locale (e.g. C.UTF-8); only honor command-line LANG=.
ifeq ($(origin LANG),command line)
QUALITY_LANGS := $(LANG)
else
QUALITY_LANGS := $(shell $(PY) -c 'from translate.lib.config import translation_langs; print(" ".join(translation_langs()))')
endif

quality:  ## Content quality (readability + style --book). Usage: make quality [LANG=ru]
	@for lang in $(QUALITY_LANGS); do \
		echo "=== $$lang: readability ==="; \
		$(PY) translate/shelf/readability.py $$lang --strict || exit 1; \
		echo "=== $$lang: style --book ==="; \
		$(PY) translate/shelf/style_check.py --book --lang $$lang --strict || exit 1; \
	done


# --- htlb-api (Go / PocketBase) ---
api-dev:  ## Run API locally on :8090
	cd $(API_DIR) && HTLB_DEV=1 HTLB_VOTE_SALT=$${HTLB_VOTE_SALT:-dev} HTLB_CORS_ORIGINS=$${HTLB_CORS_ORIGINS:-http://127.0.0.1:8000,http://localhost:8000} go run ./cmd/htlb-api serve --http=127.0.0.1:8090

api-test:  ## Go unit/integration tests (CGO_ENABLED=0)
	cd $(API_DIR) && CGO_ENABLED=0 go test ./...

api-cover:  ## Go coverage report
	cd $(API_DIR) && CGO_ENABLED=0 go test ./... -coverprofile=coverage.out
	cd $(API_DIR) && go tool cover -func=coverage.out | tail -n 1

api-lint:  ## golangci-lint + go mod tidy -diff
	cd $(API_DIR) && go mod tidy -diff
	cd $(API_DIR) && go run $(GOLANGCI_LINT) run ./...

api-format:  ## gofumpt via golangci-lint formatters
	cd $(API_DIR) && gofmt -w $$(find . -name '*.go' -not -path './.local/*')

api-build:  ## Build linux/amd64 static binary to api/bin/htlb-api
	mkdir -p $(API_DIR)/bin
	cd $(API_DIR) && CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -ldflags="-s -w -X main.Version=$$(git rev-parse --short HEAD)" -o bin/htlb-api ./cmd/htlb-api

api-smoke:  ## Smoke against ephemeral binary + pb_data
	bash $(API_DIR)/scripts/smoke.sh

api-vuln:  ## govulncheck
	cd $(API_DIR) && go run golang.org/x/vuln/cmd/govulncheck@latest ./...

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ── Upstream sync ──────────────────────────────────────────────

sync-upstream:  ## Fetch upstream CN changes (follow AGENTS.md ritual)
	@echo "→ Follow docs/pipeline/upstream-sync.md"
	git fetch upstream
	# core.quotepath=false: CJK paths must not be shell-quoted pathspecs (empty list → accidental branch switch)
	git -c core.quotepath=false ls-tree -r --name-only upstream/main book \
		| grep -E '^book/[0-9]{2}-.*\.md$$' \
		| while IFS= read -r f; do git checkout upstream/main -- "$$f"; done
	git -c core.quotepath=false ls-tree -r --name-only upstream/main docs \
		| grep -E '^docs/[^/]+\.md$$' \
		| while IFS= read -r f; do git checkout upstream/main -- "$$f"; done
	git -c core.quotepath=false ls-tree -r --name-only upstream/main docs/核实记录 \
		| while IFS= read -r f; do git checkout upstream/main -- "$$f"; done
	# Fork site serves Chinese long-reads / 核实记录 under docs/research/
	@if [ -f docs/引用对照.md ]; then cp -f docs/引用对照.md docs/research/引用对照.md; fi
	@if [ -d docs/核实记录 ]; then rsync -a --delete docs/核实记录/ docs/research/核实记录/; fi
	git checkout upstream/main -- skills/
	git show upstream/main:README.md > README.zh.md
	$(PY) forge/ops/strip_zh_readme_ads.py README.zh.md
	@echo "→ Touched CN chapters:"
	@git -c core.quotepath=false diff --name-only HEAD -- 'book/[0-9][0-9]-*.md' || true
	@echo "→ Next: fill docs/.retranslate-pending, catch up en/ru/es/pt, then check_content.py"
	@echo "→ Review: git diff -- book/ README.zh.md docs/ skills/"
	@echo "→ Never checkout ads/, site/, translate/, or forge/ from upstream"

# Zero-pad CH when set on the command line (locale LANG is unrelated).
# awk +0 forces decimal so CH=08 / CH=09 are not parsed as octal.
ifeq ($(origin CH),command line)
CH_PAD := $(shell awk 'BEGIN{printf "%02d", $(CH)+0}')
else
CH_PAD :=
endif

# ── Digest ─────────────────────────────────────────────────────

digest:  ## Split CN chapter into units. Usage: make digest CH=01
	@[ -n "$(CH)" ] || (echo "Usage: make digest CH=NN" && exit 1)
	$(PY) translate/steps/digest/make_digest.py $(CH_PAD)

# ── Assemble ───────────────────────────────────────────────────

# Canonical wave workdir; override for smoke/other runs: WORKDIR=translate/runs/smoke/ru/01
WORKDIR ?= translate/runs/active/$(LANG)/$(CH_PAD)

assemble:  ## Assemble units → book chapter. Usage: make assemble CH=02 LANG=ru [WORKDIR=…]
	@[ -n "$(CH)" ] || (echo "Usage: make assemble CH=NN LANG=ru|en|es [WORKDIR=translate/runs/active/LANG/NN]" && exit 1)
	@[ -n "$(LANG)" ] || (echo "Usage: make assemble CH=NN LANG=ru|en|es [WORKDIR=…]" && exit 1)
	$(PY) translate/steps/assemble/assemble.py $(CH_PAD) $(WORKDIR) book/$(LANG)/$(shell ls book/$(LANG)/ | grep "^$(CH_PAD)-") $(LANG)

# ── Verify ─────────────────────────────────────────────────────

verify:  ## Verify one translated chapter. Usage: make verify CH=01 LANG=ru
	@[ -n "$(CH)" ] || (echo "Usage: make verify CH=NN LANG=ru|en|es" && exit 1)
	@[ -n "$(LANG)" ] || (echo "Usage: make verify CH=NN LANG=ru|en|es" && exit 1)
	$(PY) translate/steps/verify/verify.py $(CH_PAD) --lang $(LANG) --json

verify-all:  ## Verify all chapters for a language. Usage: make verify-all LANG=ru
	@[ -n "$(LANG)" ] || (echo "Usage: make verify-all LANG=ru|en|es" && exit 1)
	@for ch in $$(ls book/$(LANG)/ | grep -oE '^[0-9]+' | sort -n | uniq); do \
		nn=$$(printf '%02d' $$ch); \
		echo "=== Chapter $$nn ($(LANG)) ==="; \
		$(PY) translate/steps/verify/verify.py $$nn --lang $(LANG) --json; \
	done

# ── Wave pipeline ───────────────────────────────────────────────

wave:  ## Run assemble+verify for a wave. Usage: make wave WAVE=1
	@[ -n "$(WAVE)" ] || (echo "Usage: make wave WAVE=N" && exit 1)
	@$(PY) -c "import json; w=json.load(open('waves.json')); print('Wave $(WAVE):', w['waves']['$(WAVE)']['chapters'])"
	@$(PY) translate/ops/wave_pipeline.py $$($(PY) -c "import json; print(' '.join(f'{int(c):02d}' for c in json.load(open('waves.json'))['waves']['$(WAVE)']['chapters']))")

repair:  ## Mechanical-first repair after verify FAIL. Usage: make repair CH=01 LANG=ru
	@[ -n "$(CH)" ] || (echo "Usage: make repair CH=NN LANG=ru|en|es|pt" && exit 1)
	@[ -n "$(LANG)" ] || (echo "Usage: make repair CH=NN LANG=ru|en|es|pt" && exit 1)
	$(PY) translate/steps/repair/repair_wave.py --nn $(CH_PAD) --lang $(LANG) \
		--workdir $(WORKDIR) --assembled $(WORKDIR)/assembled.md --max-rounds 3

# ── Status ─────────────────────────────────────────────────────

status:  ## Show translation dashboard
	$(PY) translate/ops/status.py

update-readme:  ## Audit README/OG. Usage: make update-readme [ARGS=--fix]
	$(PY) forge/ops/update_readme.py $(ARGS)

# ── Web ────────────────────────────────────────────────────────

web-build:  ## Regenerate site/{lang}/ pages from site/index.html
	$(PY) forge/site/build_pages.py

og-html:  ## Render forge/og/{en,ru,es,zh,pt,ar,id}.html from _template.html
	$(PY) forge/og/build_og_html.py

og: og-html  ## Regenerate OG PNGs from forge/og/*.html → site/assets/og/
	@mkdir -p site/assets/og
	@for lang in en ru es zh pt ar id; do \
		"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
			--headless --disable-gpu --hide-scrollbars \
			--force-device-scale-factor=1 --window-size=1200,630 \
			--screenshot=site/assets/og/$$lang.png forge/og/$$lang.html; \
		echo "✓ site/assets/og/$$lang.png"; \
	done

pages-artifact: web-build  ## Stage flat Pages tree in .publish/ (site + book + README*)
	$(PY) forge/site/pages_artifact.py

serve: pages-artifact  ## Local preview of the Pages artifact on :8000
	@echo "→ http://127.0.0.1:8000/en/"
	cd .publish && ../$(PY) -m http.server 8000

# ── Quality ────────────────────────────────────────────────────

format:  ## Auto-fix Python tools + OG HTML
	$(RUFF) format translate/ forge/
	$(RUFF) check --fix translate/ forge/
	# djlint --reformat: 0=unchanged, 1=rewrote; other codes are real failures
	@status=0; $(DJLINT) $(OG_HTML) --reformat || status=$$?; \
		if [ $$status -ne 0 ] && [ $$status -ne 1 ]; then exit $$status; fi
	$(DJLINT) $(OG_HTML) --check

lint:  ## All code linters (must match CI)
	$(RUFF) format --check translate/ forge/
	$(RUFF) check translate/ forge/
	$(DJLINT) $(OG_HTML) --check
	$(DJLINT) site/index.html --lint
	$(YAMLLINT) .github/workflows/
	shellcheck translate/steps/translate/*.sh
	@if command -v go >/dev/null 2>&1; then $(MAKE) api-lint; else echo "skip api-lint (go not on PATH)"; fi

test:  ## Run unit tests (excludes integration)
	$(PY) -m pytest translate/validate/tests/ translate/llm/tests/ forge/site/tests/ -v --ignore=translate/validate/tests/integration
	node --test forge/ebook/book.test.mjs
	@if command -v go >/dev/null 2>&1; then $(MAKE) api-test; else echo "skip api-test (go not on PATH)"; fi

ebook-deps:  ## Install forge/ebook npm dependencies
	npm ci --prefix forge/ebook

ebook-test:  ## Ebook manifest tests (chapter counts, back-links)
	node --test forge/ebook/book.test.mjs

ebook-epub: ebook-deps  ## Build one EPUB. Usage: make ebook-epub LANG=en
	@test "$(origin LANG)" = "command line" || (echo "Usage: make ebook-epub LANG=en" && exit 1)
	node forge/ebook/epub/build.mjs --lang $(LANG)

ebook-pdf: ebook-deps  ## Build one PDF. Usage: make ebook-pdf LANG=en
	@test "$(origin LANG)" = "command line" || (echo "Usage: make ebook-pdf LANG=en" && exit 1)
	node forge/ebook/pdf/build.mjs --lang $(LANG)

ebooks: ebook-deps ebook-test  ## Build EPUB+PDF for every language in langs.json
	@for lang in $$(python3 -c 'import json; print(" ".join(x["code"] for x in json.load(open("translate/langs.json"))["languages"]))'); do \
		node forge/ebook/epub/build.mjs --lang $$lang; \
		node forge/ebook/pdf/build.mjs --lang $$lang; \
	done

test-integration:  ## Run integration tests (golden manifests, E2E)
	$(PY) -m pytest translate/validate/tests/integration/ -v

lt:  ## LanguageTool on plain-terms (required; exit 2 if :8010 down). Usage: make lt CH=01 LANG=ru
	@[ -n "$(CH)" ] && [ -n "$(LANG)" ] || (echo "Usage: make lt CH=NN LANG=ru|en|es" && exit 1)
	$(PY) translate/shelf/lt_check.py --file book/$(LANG)/$(shell ls book/$(LANG)/ | grep "^$(CH_PAD)-") --lang $(LANG)

style:  ## Style audit (style_check). Usage: make style CH=10 LANG=ru
	@[ -n "$(CH)" ] && [ -n "$(LANG)" ] || (echo "Usage: make style CH=NN LANG=ru|en|es" && exit 1)
	$(PY) translate/shelf/style_check.py book/$(LANG)/$(shell ls book/$(LANG)/ | grep "^$(CH_PAD)-") --lang $(LANG)

# ── Links ──────────────────────────────────────────────────────

check-links:  ## Validate all relative links in book/ and docs/
	$(PY) forge/ops/check_links.py
