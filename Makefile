.PHONY: .uv
.uv:
	@uv -V || echo 'Please install uv: https://docs.astral.sh/uv/getting-started/installation/'

.PHONY: install-dev
install-dev: .uv
	uv sync --frozen --all-groups --all-extras

.PHONY: install
install: install-dev

.PHONY: format
format: .uv
	uv run ruff check --fix
	uv run ruff format

.PHONY: lint
lint: .uv
	uv run ruff check
	uv run ruff format --check

build: .uv
	uv build

.PHONY: test
test: .uv
	uv run pytest

.PHONY: test-verbose
test-verbose: .uv
	uv run pytest -v