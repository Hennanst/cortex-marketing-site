"""Pure control-plane checks. This module never publishes or writes remotely.

Input is a fresh Sheets snapshot (tab name -> rows including headers). Numeric
row addresses are outputs only, never durable identifiers. Sheets batchUpdate
is not compare-and-swap: callers must serialize writers with the live lease,
re-read immediately before submission and verify every field afterward.
"""
import argparse
from datetime import datetime, timezone
import json
import re

SCHEMAS = {
    "CONFIG": ("key", {"key", "value"}),
    "GATES": ("gate_id", {"gate_id", "domain_job", "gate_name", "status", "evidence_ref"}),
    "JOBS": ("job_id", {"job_id", "lane", "state", "priority", "next_gate"}),
    "RUN_CONTROL": ("lease_id", {"lease_id", "status", "run_id", "expires_at"}),
}


def table(rows, id_column, required):
    if not rows or len(set(rows[0])) != len(rows[0]) or not required <= set(rows[0]):
        raise ValueError("SCHEMA_MISMATCH")
    headers = rows[0]
    indexed = {}
    for row_index, values in enumerate(rows[1:], 1):
        if not any(v not in (None, "") for v in values):
            continue
        if len(values) > len(headers):
            raise ValueError("ROW_WIDER_THAN_SCHEMA")
        item = dict(zip(headers, values + [""] * (len(headers) - len(values))))
        key = item[id_column]
        if not key or key in indexed:
            raise ValueError(f"MISSING_OR_DUPLICATE_ID: {key}")
        indexed[key] = (row_index, item)
    return headers, indexed


def validate_snapshot(snapshot):
    indexed = {name: table(snapshot[name], key, required)[1] for name, (key, required) in SCHEMAS.items()}
    cfg = {k: row["value"] for k, (_, row) in indexed["CONFIG"].items()}
    if cfg.get("ACCOUNT_CODE") != "CO" or str(cfg.get("TAILWIND_ACCOUNT_ID")) != "1653454":
        raise ValueError("SCOPE_ROUTE_MISMATCH")
    for _, row in indexed["GATES"].values():
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", row["status"]):
            raise ValueError(f"INVALID_GATE_STATUS: {row['gate_id']}")
        if row["status"] == "PASS" and not row["evidence_ref"]:
            raise ValueError(f"PASS_WITHOUT_EVIDENCE: {row['gate_id']}")
    for _, row in indexed["JOBS"].values():
        if row["priority"] not in {"P0", "P1", "P2", "P3"} or not re.fullmatch(r"[A-Z][A-Z0-9_]*", row["state"]):
            raise ValueError(f"INVALID_JOB_STATE: {row['job_id']}")
    return indexed


def assert_lease(rows, run_id, now):
    _, records = table(rows, *SCHEMAS["RUN_CONTROL"])
    lease = records["CO-DYNAMIC-RUNNER-LEASE"][1]
    expires = datetime.fromisoformat(lease["expires_at"].replace("Z", "+00:00"))
    if not run_id or lease["status"] != "HELD" or lease["run_id"] != run_id or expires <= now:
        raise ValueError("LEASE_NOT_OWNED_OR_EXPIRED")


def plan_patch(rows, id_column, key, expected, changes):
    headers, records = table(rows, id_column, {id_column, *expected, *changes})
    if key not in records or id_column in changes:
        raise ValueError("TARGET_MISSING_OR_ID_MUTATION")
    if not changes.keys() <= expected.keys():
        raise ValueError("EXPECTED_VALUE_REQUIRED_FOR_EACH_CHANGED_FIELD")
    row_index, current = records[key]
    if any(current[k] != v for k, v in expected.items()):
        raise ValueError("STALE_STATE")
    return [{"rowIndex": row_index, "columnIndex": headers.index(k), "field": k, "before": current[k], "after": v}
            for k, v in changes.items() if current[k] != v]


def topological_order(dependencies):
    done = []
    pending = set(dependencies)
    if any(dep not in pending for deps in dependencies.values() for dep in deps):
        raise ValueError("UNKNOWN_GATE_DEPENDENCY")
    while pending:
        ready = sorted(g for g in pending if set(dependencies[g]) <= set(done))
        if not ready:
            raise ValueError("GATE_DEPENDENCY_CYCLE")
        done.extend(ready)
        pending.difference_update(ready)
    return done


def validate_evidence(evidence, candidate_sha, total, producer_run):
    if not re.fullmatch(r"[0-9a-f]{40}", candidate_sha):
        raise ValueError("FULL_CANDIDATE_SHA_REQUIRED")
    if (evidence.get("sha") != candidate_sha or evidence.get("status") != "PASS"
            or evidence.get("executed") is not True or not evidence.get("artifact")
            or evidence.get("reviewed") != total or total <= 0
            or evidence.get("unknown", 0) != 0 or not evidence.get("review_run")
            or evidence["review_run"] == producer_run):
        raise ValueError("INCOMPLETE_STALE_OR_SELF_REVIEWED_EVIDENCE")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("snapshot")
    args = parser.parse_args()
    result = validate_snapshot(json.load(open(args.snapshot)))
    print(json.dumps({"schema_status": "PASS", "rows": {k: len(v) for k, v in result.items()},
                      "scope": "CO", "release_approved": False}))
