#!/usr/bin/env bash
#
# Typechecks the codebase.
#
# Usage: ./scripts/type_check.sh

set -e
uv run mypy --config pyproject.toml nearai
uv run mypy --config pyproject.toml hub
uv run mypy --config pyproject.toml worker
