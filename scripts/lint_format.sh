#!/usr/bin/env bash
#
# Lint checks & Format checks the codebase.
#
# Usage: ./scripts/lint_format.sh

set -e
poetry run ruff check nearai/
poetry run ruff format --check --diff nearai/
