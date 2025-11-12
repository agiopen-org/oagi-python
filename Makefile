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

.PHONY: build-metapackage
build-metapackage: .uv
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
	@if [ -z "$(VERSION)" ]; then \
		echo "Usage: make version VERSION=x.y.z"; \
		echo "Current version: $$(grep '^version = ' pyproject.toml | head -1 | cut -d'"' -f2)"; \
		exit 1; \
	fi
	@echo "Updating version to $(VERSION) in all files..."
	@sed -i '' 's/^version = ".*"/version = "$(VERSION)"/' pyproject.toml
	@sed -i '' 's/^version = ".*"/version = "$(VERSION)"/' metapackage/pyproject.toml
	@sed -i '' 's/oagi-core\[desktop,server\]==.*/oagi-core[desktop,server]==$(VERSION)",/' metapackage/pyproject.toml
	@echo "✓ Updated root pyproject.toml"
	@echo "✓ Updated metapackage/pyproject.toml"
	@echo "✓ Updated metapackage dependency to oagi-core==$(VERSION)"
	@echo ""
	@echo "Don't forget to:"
	@echo "  1. git add pyproject.toml metapackage/pyproject.toml"
	@echo "  2. git commit -m 'release: $(VERSION)'"
	@echo "  3. git tag v$(VERSION)"
	@echo "  4. git push && git push --tags"