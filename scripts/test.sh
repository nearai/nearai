#!/usr/bin/env bash
#
# Runs tests on the codebase.
#
# Usage: ./scripts/test.sh

set -e
poetry run pytest
