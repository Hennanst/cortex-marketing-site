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
    "LOCKS": ("lock_id", {"lock_id", "scope", "status", "release_condition"}),
    "STATE": ("state_id", {"state_id", "domain", "status"}),
    "TRANSACTIONS": ("tx_id", {"tx_id", "target_id", "operation"}),
}

SHEET_IDS = {"CONFIG": 607237811, "GATES": 1763579041, "JOBS": 349981761,
             "STATE": 1212961709, "RECOVERY": 912609060}
IDENTITY_FIELDS = {"GATES": {"gate_id", "domain_job", "gate_name"},
                   "JOBS": {"job_id", "lane", "object"},
                   "STATE": {"state_id", "domain"}}
PROTECTED_STATE_TOKENS = {"PASS", "RELEASED", "QUEUED", "PUBLISHED"}
RELEASE_DAG = {
    "RG2": [], "RG3": ["RG2"], "RG4": ["RG3"], "RG5": ["RG4"],
    "RG6": ["RG5"], "RG7": ["RG6"], "RG7A": ["RG7"],
    "DEPLOY": ["RG7A"], "RG8": ["DEPLOY"], "RG9": ["RG8"], "RG10": ["RG9"],
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
    if (cfg.get("CANONICAL_HOST", "").rstrip("/") != "https://cortex-ofertas.pages.dev"
            or cfg.get("AFFILIATE_TAG") != "cortexofertas-20"
            or cfg.get("GITHUB_MARKETING_REPO") != "Hennanst/cortex-marketing-site"):
        raise ValueError("PRODUCTION_ROUTE_MISMATCH")
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
    if "CO-DYNAMIC-RUNNER-LEASE" not in records:
        raise ValueError("LEASE_MISSING_OR_INVALID")
    lease = records["CO-DYNAMIC-RUNNER-LEASE"][1]
    try:
        expires = datetime.fromisoformat(lease["expires_at"].replace("Z", "+00:00"))
        if expires.utcoffset() is None or now.utcoffset() is None:
            raise ValueError("timezone required")
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError("LEASE_MISSING_OR_INVALID") from exc
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
            or type(total) is not int or total <= 0
            or type(evidence.get("reviewed")) is not int or evidence["reviewed"] != total
            or type(evidence.get("unknown")) is not int or evidence["unknown"] != 0
            or not producer_run or not evidence.get("review_run")
            or evidence["review_run"] == producer_run):
        raise ValueError("INCOMPLETE_STALE_OR_SELF_REVIEWED_EVIDENCE")


def plan_mutation(snapshot, plan, run_id, now):
    """Validate state patches; emit minimal Sheets updates plus readback contract.

    Public side effects and approval of gates deliberately have no generic path
    through this helper. They require their dedicated independent release review.
    """
    indexed = validate_snapshot(snapshot)
    assert_lease(snapshot["RUN_CONTROL"], run_id, now)
    cfg = {key: row["value"] for key, (_, row) in indexed["CONFIG"].items()}
    if plan.get("execution_context") not in {"manual", "scheduled"}:
        raise ValueError("EXECUTION_CONTEXT_REQUIRED")
    if plan["execution_context"] == "scheduled" and cfg.get("OFFICE_EXECUTION_MODE") == "MANUAL_MAINTENANCE":
        raise ValueError("SCHEDULERS_PAUSED")
    if plan.get("operation") != "state_patch":
        raise ValueError("DEDICATED_REVIEW_REQUIRED_FOR_EXTERNAL_OPERATION")
    if not plan.get("external_ref") or not plan.get("tx_id"):
        raise ValueError("PERSISTED_ARTIFACT_AND_TRANSACTION_REQUIRED")
    if plan["tx_id"] in indexed["TRANSACTIONS"]:
        raise ValueError("TRANSACTION_ALREADY_EXISTS_RECONCILE_NO_REPLAY")
    if not plan.get("patches"):
        raise ValueError("EMPTY_BUSINESS_MUTATION")
    requests, readback, seen = [], [], set()
    for patch in plan["patches"]:
        name, key, changes = patch["tab"], patch["id"], patch["changes"]
        if name not in SHEET_IDS or name in {"CONFIG", "RECOVERY"}:
            raise ValueError("NORMATIVE_OR_RELEASE_STATE_REQUIRES_DEDICATED_REVIEW")
        if name == "STATE" and key == "CO-GLOBAL":
            raise ValueError("GLOBAL_RELEASE_STATE_REQUIRES_DEDICATED_REVIEW")
        if IDENTITY_FIELDS.get(name, set()) & changes.keys():
            raise ValueError("IMMUTABLE_TARGET_IDENTITY")
        if any(v in {"PASS", "RELEASED", "QUEUED", "PUBLISHED"} for v in changes.values() if isinstance(v, str)):
            raise ValueError("GATE_OR_EXTERNAL_SUCCESS_REQUIRES_DEDICATED_REVIEW")
        if "priority" in changes and changes["priority"] not in {"P0", "P1", "P2", "P3"}:
            raise ValueError("INVALID_PRIORITY")
        for field in {"state", "status"} & changes.keys():
            if not isinstance(changes[field], str) or not re.fullmatch(r"[A-Z][A-Z0-9_]*", changes[field]):
                raise ValueError("INVALID_STATE_VALUE")
            if set(changes[field].split("_")) & PROTECTED_STATE_TOKENS:
                raise ValueError("GATE_OR_EXTERNAL_SUCCESS_REQUIRES_DEDICATED_REVIEW")
        rows = snapshot[name]
        id_column = SCHEMAS[name][0]
        if key not in indexed[name]:
            raise ValueError("TARGET_MISSING_OR_ID_MUTATION")
        current = indexed[name][key][1]
        # Approved records and their evidence cannot be silently overwritten,
        # even when the proposed patch only changes a timestamp or evidence URL.
        if any(set(str(current.get(f, "")).split("_")) & PROTECTED_STATE_TOKENS
               for f in ("status", "state")) and any(current.get(k) != v for k, v in changes.items()):
            raise ValueError("APPROVED_STATE_CHANGE_REQUIRES_JUSTIFIED_REVIEW")
        fields = plan_patch(rows, id_column, key, patch["expected"], changes)
        for field in fields:
            cell_key = (name, key, field["field"])
            if cell_key in seen:
                raise ValueError("DUPLICATE_FIELD_PATCH")
            seen.add(cell_key)
            value = field["after"]
            if not isinstance(value, str):
                raise ValueError("STATE_FIELDS_MUST_BE_TEXT")
            requests.append({"updateCells": {"start": {"sheetId": SHEET_IDS[name],
                              "rowIndex": field["rowIndex"], "columnIndex": field["columnIndex"]},
                              "rows": [{"values": [{"userEnteredValue": {"stringValue": value}}]}],
                              "fields": "userEnteredValue"}})
            readback.append({"tab": name, "id": key, "field": field["field"], "value": value})
    if not requests:
        raise ValueError("NO_CHANGE_USE_RUNS_HEARTBEAT")
    return {"status": "PATCH_PLAN_VALID", "requests": requests, "readback": readback,
            "tx_id": plan["tx_id"], "external_ref": plan["external_ref"],
            "requires_atomic_transaction_append": True,
            "external_operation_authorized": False,
            "warning": "Re-read lease and expected state before submitting with transaction. Verify IDs and values afterward."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("snapshot")
    parser.add_argument("--plan")
    parser.add_argument("--run-id")
    args = parser.parse_args()
    with open(args.snapshot) as source:
        snapshot = json.load(source)
    if args.plan:
        with open(args.plan) as source:
            result = plan_mutation(snapshot, json.load(source), args.run_id, datetime.now(timezone.utc))
    else:
        indexed = validate_snapshot(snapshot)
        result = {"schema_status": "PASS", "rows": {k: len(v) for k, v in indexed.items()},
                  "scope": "CO", "release_approved": False,
                  "proposed_release_order": topological_order(RELEASE_DAG),
                  "release_order_is_authorization": False}
    print(json.dumps(result, ensure_ascii=False))
