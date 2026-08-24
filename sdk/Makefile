.PHONY: spec generate generate-facade test lint typecheck build

API_DIR := ../api
GENERATED_STAGING := .generated-staging

# Refresh OpenAPI snapshot from api/ application code (no running server required)
spec:
	cd $(API_DIR) && uv run python manage.py dump_openapi --output ../sdk/openapi.json

# Regenerate ocmo/_generated/ from committed openapi.json
generate:
	rm -rf $(GENERATED_STAGING)
	uv run openapi-python-client generate \
		--path openapi.json \
		--config openapi-python-client.yaml \
		--output-path $(GENERATED_STAGING) \
		--overwrite
	rm -rf ocmo/_generated
	mkdir -p ocmo/_generated
	cp -a $(GENERATED_STAGING)/ocmo._generated/. ocmo/_generated/
	rm -rf $(GENERATED_STAGING)
	uv run python scripts/generate_facade.py

# Regenerate ocmo/_facade_impl.py from ocmo/_generated/api/
generate-facade:
	uv run python scripts/generate_facade.py
build:
	uv build

# Run tests
test:
	uv run pytest

# Lint
lint:
	uv run ruff check ocmo/ tests/

# Type-check
typecheck:
	uv run mypy ocmo/ --exclude ocmo/_generated
