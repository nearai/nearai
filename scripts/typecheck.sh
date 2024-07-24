#!/usr/bin/env bash
#
# Typechecks the codebase.
#
# Usage: ./scripts/typecheck.sh

set -e
poetry run mypy nearai/
