#!/usr/bin/env bash
#
# Format checks the codebase.
#
# Usage: ./scripts/format_check.sh

set -e
poetry run ruff format --check --diff nearai/
