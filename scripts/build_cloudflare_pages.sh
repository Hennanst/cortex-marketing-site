#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# Audit first: stale source cannot produce a deployable bundle.
python3 "$ROOT/scripts/recovery_source_truth_guard.py" --root "$ROOT" --source-only
python3 "$ROOT/scripts/public_bundle.py"
python3 "$ROOT/scripts/apply_premium_visuals.py" "$ROOT/dist"
python3 "$ROOT/scripts/recovery_source_truth_guard.py" --root "$ROOT" --compare-dist
echo "RG6_BUILD_PURITY_PACKAGE_PASS"
