.PHONY: .uv
.uv:
	@uv -V || echo 'Please install uv: https://docs.astral.sh/uv/getting-started/installation/'

.PHONY: install-dev
install-dev: .uv
	uv sync --all-groups --all-extras

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

.PHONY: build
build: .uv
	uv build

.PHONY: sync-metapackage-files
sync-metapackage-files:
	@echo "Syncing README.md and LICENSE to metapackage..."
	@cp README.md metapackage/README.md
	@cp LICENSE metapackage/LICENSE

.PHONY: build-metapackage
build-metapackage: .uv sync-metapackage-files
	cd metapackage && uv build

.PHONY: build-all
build-all: build build-metapackage

.PHONY: test
test: .uv install-dev
	uv run pytest

.PHONY: test-verbose
test-verbose: .uv install-dev
	uv run pytest -v

.PHONY: version
version:
	@if [ -n "$(filter-out $@,$(MAKECMDGOALS))" ]; then \
		VERSION=$(filter-out $@,$(MAKECMDGOALS)); \
	else \
		echo "Usage: make version <version>"; \
		exit 1; \
	fi; \
	echo "Updating version to $$VERSION..."; \
	uv version $$VERSION; \
	(cd metapackage && uv version $$VERSION); \
	sed -i '' 's/oagi-core\[desktop,server\]==.*/oagi-core[desktop,server]=='$$VERSION'",/' metapackage/pyproject.toml; \
	make build-all

%:
	@: