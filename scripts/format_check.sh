#!/usr/bin/env bash
#
# Format checks the codebase.
#
# Usage: ./scripts/format_check.sh

set -e
uv run ruff format --check --diff .
