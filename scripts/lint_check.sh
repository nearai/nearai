#!/usr/bin/env bash
#
# Lint checks the codebase.
#
# Usage: ./scripts/lint_check.sh

set -e
uv run ruff check .
