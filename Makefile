.PHONY: install install-tools hub gui test lint fmt check

install:
	pip install -e ".[dev]"

install-tools:
	bash scripts/install_tools.sh

hub:
	python3 -m forensicx_hub

gui:
	python3 -m forensicx gui

check-android:
	bash scripts/check_android.sh

test:
	pytest --tb=short

lint:
	ruff check src tests forensicx_hub

fmt:
	ruff format src tests forensicx_hub

check: lint test

clean:
	find . -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
	find . -name '*.pyc' -delete 2>/dev/null || true
	rm -rf .pytest_cache .ruff_cache htmlcov .coverage forensicx.db
