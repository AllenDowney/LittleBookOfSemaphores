PROJECT_NAME = LittleBookOfSemaphores

.PHONY: help create_environment create_environment_dev delete_environment \
	update_environment update_environment_dev clean lint format tests

help:
	@echo "Available targets:"
	@echo "  create_environment      - Create conda environment from environment.yml"
	@echo "  create_environment_dev  - Create dev environment (base + pytest/black/flake8)"
	@echo "  delete_environment      - Remove conda environment"
	@echo "  update_environment      - Update environment from environment.yml (with --prune)"
	@echo "  update_environment_dev  - Update dev environment"
	@echo "  clean                   - Remove temporary files and caches"
	@echo "  lint                    - Run linters (flake8, black --check)"
	@echo "  format                  - Format code with black"
	@echo "  tests                   - Run Sync tests"

## Set up Python environment
create_environment:
	mamba env create -y -f environment.yml
	@echo ""
	@echo ">>> Environment created successfully!"
	@echo ">>> Activate with: conda activate $(PROJECT_NAME)"

## Create dev environment (base + test/lint tools)
create_environment_dev: create_environment
	mamba env update -y -f environment-dev.yml --name $(PROJECT_NAME)
	@echo ""
	@echo ">>> Dev environment created successfully!"
	@echo ">>> Activate with: conda activate $(PROJECT_NAME)"
	@echo ">>> CI / pip-only equivalent: pip install -r requirements-dev.txt"

## Delete environment
delete_environment:
	mamba env remove -y --name $(PROJECT_NAME)
	@echo ">>> Environment $(PROJECT_NAME) removed"

## Update environment
update_environment:
	mamba env update -y -f environment.yml --name $(PROJECT_NAME) --prune
	@echo ">>> Environment updated successfully!"

## Update dev environment
update_environment_dev: update_environment
	mamba env update -y -f environment-dev.yml --name $(PROJECT_NAME) --prune
	@echo ">>> Dev environment updated successfully!"

## Run tests
tests:
	@echo "Running tests..."
	cd code && python -m pytest sync_core_test.py Sync_test.py Gui_test.py -q
	@echo ">>> Tests complete!"

## Run linters (check only) — Sync engine + tests; not Gui or sync_code examples
lint:
	@echo "Running linters..."
	flake8 code/sync_core.py code/Sync.py code/sync_core_test.py code/Sync_test.py
	black --check --config pyproject.toml code/sync_core.py code/Sync.py code/sync_core_test.py code/Sync_test.py
	@echo ">>> Linting complete!"

## Format code
format:
	@echo "Formatting code..."
	black --config pyproject.toml code/sync_core.py code/Sync.py code/sync_core_test.py code/Sync_test.py
	@echo ">>> Formatting complete!"

## Clean temporary files and caches
clean:
	@echo "Cleaning temporary files and caches..."
	-find . -type f -name "*.py[co]" -delete
	-find . -type d -name "__pycache__" -delete
	-find . -type d -name ".pytest_cache" -delete
	-find . -type d -name ".ipynb_checkpoints" -delete
	-rm -rf .ruff_cache/
	-rm -rf .mypy_cache/
	-rm -rf build/
	-rm -rf dist/
	-rm -rf *.egg-info
	@echo ">>> Cleanup complete!"
