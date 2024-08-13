#!/usr/bin/env bash
#
# Builds docs.
#
# Usage: ./scripts/build_mkdocs.sh

set -e
poetry run mkdocs build
