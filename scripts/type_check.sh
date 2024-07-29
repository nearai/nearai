#!/usr/bin/env bash
#
# Typechecks the codebase.
#
# Usage: ./scripts/type_check.sh

set -e
poetry run mypy --config pyproject.toml nearai
poetry run mypy --config pyproject.toml hub
