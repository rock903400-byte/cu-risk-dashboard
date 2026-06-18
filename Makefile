PY ?= python
BLACK := $(PY) -m black
FLAKE8 := $(PY) -m flake8
MYPY := $(PY) -m mypy
PYTEST := $(PY) -m pytest

SRC := .
TESTS := tests

.PHONY: help fmt fmt-check lint type test review verify all clean cache

help:
	@echo "Targets:"
	@echo "  make fmt        - black 格式化全部 source"
	@echo "  make fmt-check  - black --check（CI 用，不改檔）"
	@echo "  make lint       - flake8"
	@echo "  make type       - mypy"
	@echo "  make test       - pytest -v"
	@echo "  make review     - git status + diff stat（人工 review 摘要）"
	@echo "  make verify     - 跑全部檢查（lint + type + test），一錯就停"
	@echo "  make all        - fmt + verify（CI 前置）"
	@echo "  make clean      - 清 __pycache__ / .mypy_cache / .pytest_cache"

fmt:
	$(BLACK) $(SRC)

fmt-check:
	$(BLACK) --check $(SRC)

lint:
	$(FLAKE8) $(SRC)

type:
	$(MYPY) $(SRC)

test:
	$(PYTEST) $(TESTS) -v

review:
	@echo "=== git status ==="
	@git status --short
	@echo ""
	@echo "=== diff stat ==="
	@git diff --stat
	@echo ""
	@echo "=== staged stat ==="
	@git diff --cached --stat

verify: lint type test

all: fmt verify

clean:
	@echo "Removing caches..."
	@$(PY) -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in [pathlib.Path('__pycache__'), pathlib.Path('.mypy_cache'), pathlib.Path('.pytest_cache')]]"
	@find . -type d -name __pycache__ -not -path '*/\.*' -exec rm -rf {} + 2>/dev/null || true
