"""Deterministic claim, anomaly, confidence, coverage, and rollup judgment."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit

from client_side_rules import MISSING, evaluate_business_rule, path_value, path_values
from value_semantics import strict_equal

from .constants import DOMAINS, compact_reason, worst_status
from .correlate import action_evidence, build_model, source_event_names
from .coverage import coverage_result, event_by_id
from .predicates import evaluate_predicate, predicate_expected
from .state import canonical_json


def _summary(value: Any, *, depth: int = 0) -> Any:
    if value is MISSING:
        return "<absent>"
    if depth > 3:
        return "<nested>"
    if isinstance(value, str):
        return value if len(value) <= 160 else value[:157] + "..."
    if isinstance(value, list):
        return [_summary(item, depth=depth + 1) for item in value[:5]] + (
            [f"... {len(value) - 5} more"] if len(value) > 5 else []
        )
    if isinstance(value, dict):
        keys = list(value)[:10]
        output = {str(key): _summary(value[key], depth=depth + 1) for key in keys}
        if len(value) > 10:
            output["..."] = f"{len(value) - 10} more keys"
        return output
    return value


def _one_or_distinct(values: list[Any]) -> Any:
    distinct: list[Any] = []
    seen: set[str] = set()
    for value in values:
        key = canonical_json(value)
        if key not in seen:
            seen.add(key)
            distinct.append(value)
    return distinct[0] if len(distinct) == 1 else distinct if distinct else MISSING


def _path_observations(payloads: list[Any], path: str) -> Any:
    values = [value for payload in payloads for value in path_values(payload, path)]
    if "[]" in path or "[*]" in path:
        return values if values else MISSING
    return _one_or_distinct(values)


def _evaluate_claim_value(
    actual: Any, claim: dict[str, Any], *, wire: bool = False
) -> dict[str, Any]:
    predicate = claim.get("predicate", {})
    path = str(claim.get("target", {}).get("path") or "")
    operator = predicate.get("operator")
    if (
        isinstance(actual, list)
        and ("[]" in path or "[*]" in path)
        and operator not in {"count", "order"}
    ):
        results = [evaluate_predicate(value, predicate, wire=wire) for value in actual]
        failing = next((result for result in results if result["status"] != "PASS"), None)
        return failing or {
            "status": "PASS",
            "reason_code": "predicate.pass",
            "reason": f"Predicate satisfied by all {len(actual)} addressed values.",
        }
    return evaluate_predicate(actual, predicate, wire=wire)


def _inspection(
    claim: dict[str, Any],
    status: str,
    reason_code: str,
    reason: str,
    *,
    observed: Any = None,
    expected: Any = None,
    evidence: list[str] | None = None,
    check_next: str | None = None,
    scenario_id: str | None = None,
) -> dict[str, Any]:
    target = claim.get("target", {})
    return {
        "claim_id": claim.get("claim_id"),
        "scenario_id": scenario_id,
        "domain": claim.get("domain"),
        "inspection_target": claim.get("label") or target.get("label") or target.get("check"),
        "status": status,
        "reason_code": reason_code,
        "reason": compact_reason(reason),
        "observed": _summary(observed),
        "expected": _summary(
            predicate_expected(claim.get("predicate", {})) if expected is None else expected
        ),
        "check_next": check_next,
        "evidence": list(dict.fromkeys(str(item) for item in (evidence or []) if item)),
        "target": target,
    }


def _actions_for_event(model: dict[str, Any], event_id: str) -> list[dict[str, Any]]:
    return [
        action
        for action in model["actions"]
        if event_id in {str(value) for value in action.get("event_ids", [])}
    ]


def _scenario_groups(
    model: dict[str, Any], event: dict[str, Any], coverage: dict[str, Any]
) -> list[dict[str, Any]]:
    actions = {
        action["action_id"]: action for action in _actions_for_event(model, event["event_id"])
    }
    groups = []
    for scenario in coverage.get("scenarios", []):
        if not isinstance(scenario, dict):
            continue
        selected = [
            actions[action_id]
            for action_id in map(str, scenario.get("action_ids", []))
            if action_id in actions
        ]
        groups.append(
            {
                "scenario_id": str(scenario.get("scenario_id") or "ordinary"),
                "label": str(scenario.get("label") or scenario.get("scenario_id") or "Scenario"),
                "values": scenario.get("values", {}),
                "actions": selected,
                "behavior_signature": scenario.get("behavior_signature"),
            }
        )
    known = {group["scenario_id"] for group in groups}
    for action in actions.values():
        scenario_id = str(action.get("scenario_id") or "ordinary")
        if scenario_id not in known:
            groups.append(
                {
                    "scenario_id": scenario_id,
                    "label": str(action.get("scenario_label") or scenario_id),
                    "values": action.get("scenario_values", {}),
                    "actions": [action],
                    "behavior_signature": None,
                }
            )
            known.add(scenario_id)
        elif (
            action
            not in next(group for group in groups if group["scenario_id"] == scenario_id)["actions"]
        ):
            next(group for group in groups if group["scenario_id"] == scenario_id)[
                "actions"
            ].append(action)
    return groups


def _applicable(claim: dict[str, Any], scenario: dict[str, Any]) -> bool | None:
    condition = claim.get("applicability")
    if not condition:
        return True
    if not isinstance(condition, dict) or not condition.get("path"):
        return None
    actual = path_value(scenario.get("values", {}), str(condition["path"]))
    if actual is MISSING:
        return None
    predicate = (
        condition.get("predicate") if isinstance(condition.get("predicate"), dict) else condition
    )
    result = evaluate_predicate(actual, predicate)
    if result["status"] == "PASS":
        return True
    if result["status"] == "FAIL":
        return False
    return None


def _evidence_collection_complete(evidence: dict[str, list[dict[str, Any]]], adapter: str) -> bool:
    if adapter == "preview":
        return any(
            row.get("complete") is True and row.get("event_list_complete") is True
            for row in evidence.get("preview_windows", [])
        ) or _preview_complete(evidence.get("preview_events", []), "event_list")
    if adapter == "network":
        return any(
            row.get("complete") is True for row in evidence.get("network_windows", [])
        ) or any(
            row.get("collection_complete") is True for row in evidence.get("logical_sends", [])
        )
    return False


def _capability(model: dict[str, Any], surface: str) -> bool | str:
    profile = model.get("capability")
    if not isinstance(profile, dict):
        return "unknown"
    return profile.get("surfaces", {}).get(surface, "unknown")


def _binding_for_evidence(
    model: dict[str, Any],
    evidence: dict[str, list[dict[str, Any]]],
    action: dict[str, Any] | None,
) -> tuple[dict[str, Any] | None, set[str]]:
    action_id = action.get("action_id") if isinstance(action, dict) else None
    document_ids = {
        str(row.get("document_id"))
        for key in ("pages", "source_calls", "requests")
        for row in evidence.get(key, [])
        if row.get("document_id")
        # A navigation action is expected to start on one document and produce its
        # measurement evidence on the next. Keep the before page for business/reality
        # comparisons, but do not treat it as an occurrence-document conflict.
        and not (key == "pages" and row.get("phase") == "before")
    }
    bindings = model.get("bindings", [])
    binding = next(
        (row for row in reversed(bindings) if action_id and row.get("action_id") == action_id),
        None,
    )
    if binding is None and document_ids:
        binding = next(
            (
                row
                for row in reversed(bindings)
                if str(row.get("document_id") or "") in document_ids
            ),
            None,
        )
    if binding is None and len(bindings) == 1:
        binding = bindings[0]
    if binding is None and isinstance(model.get("binding"), dict):
        binding = model["binding"]
    return binding, document_ids


def _binding_identity_mismatch(
    binding: dict[str, Any],
    document_ids: set[str],
    evidence: dict[str, list[dict[str, Any]]],
    *,
    expected_containers: set[str],
    action_id: str | None,
) -> dict[str, Any] | None:
    bound_document = str(binding.get("document_id") or "")
    foreign_documents = sorted(
        value for value in document_ids if bound_document and value != bound_document
    )
    preview_epochs = {
        str(row.get("epoch")) for row in evidence.get("preview_events", []) if row.get("epoch")
    }
    bound_epoch = str(binding.get("preview_epoch") or "")
    foreign_epochs = sorted(
        value for value in preview_epochs if bound_epoch and value != bound_epoch
    )
    foreign_preview = [
        row.get("occurrence_id")
        for row in evidence.get("preview_events", [])
        if expected_containers
        and not expected_containers.issubset(
            {str(value) for value in row.get("container_ids", []) if value}
        )
    ]
    unbound_worker_requests = [
        row.get("request_id")
        for row in evidence.get("requests", [])
        if row.get("document_id") in (None, "")
        and row.get("worker_id") not in (None, "")
        and (
            not action_id
            or str(row.get("action_id") or "") != action_id
            or (
                row.get("browser_context_id") not in (None, binding.get("browser_context_id"))
                or row.get("tab_id") not in (None, binding.get("tab_id"))
            )
        )
    ]
    if (
        not foreign_documents
        and not foreign_epochs
        and not foreign_preview
        and not unbound_worker_requests
    ):
        return None
    refs = [
        binding.get("evidence_ref"),
        *[
            row.get("evidence_ref")
            for key in ("pages", "source_calls", "requests")
            for row in evidence.get(key, [])
        ],
    ]
    return {
        "observed": {
            "bound_document": bound_document,
            "evidence_documents": sorted(document_ids),
            "bound_preview_epoch": bound_epoch,
            "evidence_preview_epochs": sorted(preview_epochs),
            "expected_preview_containers": sorted(expected_containers),
            "foreign_preview_occurrences": foreign_preview,
            "unattributed_worker_requests": unbound_worker_requests,
        },
        "evidence": refs,
    }


def _container_binding(
    binding: dict[str, Any], plan: dict[str, Any]
) -> tuple[str, str, str, dict[str, Any]]:
    expected = set(plan.get("scope", {}).get("expected_container", []))
    natural = set(binding.get("natural_container_ids", []))
    overrides = set(binding.get("override_container_ids", []))
    active = set(binding.get("active_container_ids", [])) or natural | overrides
    if expected and not expected.issubset(natural):
        allowed = plan.get("scope", {}).get("allow_container_override") is True
        if not (allowed and expected.issubset(active) and expected.issubset(overrides)):
            return (
                "FAIL",
                "binding.natural_container_mismatch",
                "The active runtime does not prove the expected container under the approved binding mode.",
                {
                    "natural": sorted(natural),
                    "active": sorted(active),
                    "expected": sorted(expected),
                },
            )
        return (
            "PASS",
            "binding.current",
            "Current origin/document and explicitly approved Preview container override are attributable.",
            {"override_used": True},
        )
    return (
        "PASS",
        "binding.current",
        "Current origin, document, and natural container binding are attributable.",
        {"override_used": False},
    )


def _binding_result(
    event: dict[str, Any],
    plan: dict[str, Any],
    model: dict[str, Any],
    scenario_id: str,
    evidence: dict[str, list[dict[str, Any]]] | None = None,
    action: dict[str, Any] | None = None,
) -> dict[str, Any]:
    claim = {
        "claim_id": f"{event['event_id']}::BINDING",
        "domain": "reality",
        "target": {"check": "binding", "label": "Live browser/Preview binding"},
        "predicate": {"operator": "present"},
        "label": "Live browser/Preview binding",
    }
    evidence = evidence or {}
    binding, document_ids = _binding_for_evidence(model, evidence, action)
    if not isinstance(binding, dict):
        return _inspection(
            claim,
            "BLOCKED",
            "binding.missing",
            "No live browser/document binding was captured.",
            expected="Current approved origin, document, and Preview linkage",
            check_next="Managed Playwright target and Tag Assistant connection",
            scenario_id=scenario_id,
        )

    approved = {
        urlsplit(value).netloc.casefold() for value in plan.get("scope", {}).get("origins", [])
    }
    observed_host = urlsplit(str(binding.get("origin") or "")).netloc.casefold()
    if observed_host not in approved:
        return _inspection(
            claim,
            "BLOCKED",
            "binding.origin_unapproved",
            "The bound document is not on an approved origin.",
            observed=binding.get("origin"),
            expected=plan.get("scope", {}).get("origins", []),
            evidence=[binding.get("evidence_ref")],
            check_next="Current target tab/origin",
            scenario_id=scenario_id,
        )

    expected_containers = set(plan.get("scope", {}).get("expected_container", [])) or set(
        binding.get("active_container_ids", [])
    )
    mismatch = _binding_identity_mismatch(
        binding,
        document_ids,
        evidence,
        expected_containers=expected_containers,
        action_id=action.get("action_id") if isinstance(action, dict) else None,
    )
    if mismatch is not None:
        return _inspection(
            claim,
            "BLOCKED",
            "binding.occurrence_identity_mismatch",
            "Occurrence evidence belongs to another document or Preview epoch.",
            observed=mismatch["observed"],
            expected="One attributable document and Preview epoch",
            evidence=mismatch["evidence"],
            check_next="Current document/frame and Tag Assistant epoch",
            scenario_id=scenario_id,
        )

    status, code, reason, container = _container_binding(binding, plan)
    if status == "FAIL":
        return _inspection(
            claim,
            status,
            code,
            reason,
            observed={"natural": container["natural"], "active": container["active"]},
            expected=container["expected"],
            evidence=[binding.get("evidence_ref")],
            check_next="Natural page container bootstrap or explicitly approved Preview override",
            scenario_id=scenario_id,
        )
    return _inspection(
        claim,
        status,
        code,
        reason,
        observed={
            key: binding.get(key)
            for key in (
                "origin",
                "document_id",
                "natural_container_ids",
                "active_container_ids",
                "override_container_ids",
                "preview_epoch",
            )
        },
        expected="Approved live binding",
        evidence=[binding.get("evidence_ref")],
        scenario_id=scenario_id,
    )


def _page_result(
    claim: dict[str, Any],
    evidence: dict[str, list[dict[str, Any]]],
    event: dict[str, Any],
    scenario_id: str,
) -> dict[str, Any]:
    pages = evidence["pages"]
    after = next(
        (page for page in reversed(pages) if page.get("phase") == "after"),
        pages[-1] if pages else None,
    )
    if after is None:
        return _inspection(
            claim,
            "BLOCKED",
            "reality.not_observed",
            "No attributable page/business outcome was captured.",
            expected="Valid intended page and action outcome",
            check_next="Target page/API outcome",
            scenario_id=scenario_id,
        )
    status_code = after.get("status_code")
    completion = after.get("completion") if isinstance(after.get("completion"), dict) else {}
    failures = []
    if isinstance(status_code, int) and status_code >= 400:
        failures.append(f"HTTP {status_code}")
    if after.get("soft_404") is True or after.get("page_valid") is False:
        failures.append("dead/invalid rendered page")
    if after.get("target_present") is False:
        failures.append("intended interaction target absent")
    if completion.get("succeeded") is False:
        failures.append("user-visible action failed")
    expected_url = event.get("journey", {}).get("url")
    if (
        expected_url
        and after.get("url")
        and urlsplit(str(expected_url)).path != urlsplit(str(after["url"])).path
    ):
        failures.append("unexpected route")
    if failures:
        return _inspection(
            claim,
            "FAIL",
            "reality.invalid_outcome",
            "; ".join(failures) + ".",
            observed={
                "url": after.get("url"),
                "status_code": status_code,
                "completion": completion,
            },
            expected="Valid intended page and successful applicable action",
            evidence=[after.get("evidence_ref")],
            check_next="Page/API response and visible business outcome",
            scenario_id=scenario_id,
        )
    predicate = claim.get("predicate", {})
    target = claim.get("target", {})
    if target.get("check") == "page_value":
        path = str(target.get("path") or "")
        actual = path_value(after, path)
        if actual is MISSING:
            actual = path_value({"page": after, "business": after.get("business", {})}, path)
        result = evaluate_predicate(actual, predicate)
        return _inspection(
            claim,
            result["status"],
            f"reality.{result['reason_code']}",
            result["reason"],
            observed=actual,
            evidence=[after.get("evidence_ref")],
            check_next=f"Visible page/business value {path}"
            if result["status"] != "PASS"
            else None,
            scenario_id=scenario_id,
        )
    if target.get("check") == "relationship":
        payload = {"page": after, "business": after.get("business", {})}
        result = evaluate_business_rule(predicate.get("relationship", {}), payload)
        return _inspection(
            claim,
            result["status"],
            f"business.{result.get('operator') or 'relationship'}",
            result.get("reason", "Business relationship evaluated."),
            observed=result.get("actual"),
            expected=result.get("expected"),
            evidence=[after.get("evidence_ref")],
            check_next="Visible business state and relation inputs",
            scenario_id=scenario_id,
        )
    return _inspection(
        claim,
        "PASS",
        "reality.valid",
        "The intended page and action outcome are valid.",
        observed={
            "url": after.get("url"),
            "status_code": status_code,
            "business": after.get("business"),
        },
        expected="Valid intended page and action outcome",
        evidence=[after.get("evidence_ref")],
        scenario_id=scenario_id,
    )


def _settlement_inspection(
    event: dict[str, Any],
    evidence: dict[str, list[dict[str, Any]]],
    scenario_id: str,
) -> dict[str, Any]:
    claim = {
        "claim_id": f"{event['event_id']}::SETTLEMENT",
        "domain": "behavior",
        "target": {"check": "settlement", "label": "Action settlement"},
        "predicate": {"operator": "present"},
        "label": "Action settlement",
    }
    health = [row for row in evidence.get("health", []) if row.get("phase") == "after"]
    latest = health[-1] if health else None
    if latest is None:
        return _inspection(
            claim,
            "BLOCKED",
            "settlement.unobserved",
            "No action-bound post-interaction health/settlement evidence was captured.",
            expected="Settled action boundary",
            check_next="Collector health and bounded quiet/pending evidence state",
            scenario_id=scenario_id,
        )
    if latest.get("settled") is not True:
        return _inspection(
            claim,
            "BLOCKED",
            "settlement.unstable",
            "The action boundary remained unsettled, so late evidence may still change the verdict.",
            observed={
                "status": latest.get("status"),
                "settled": latest.get("settled"),
                "reason": latest.get("settlement_reason"),
            },
            expected="Settled action boundary",
            evidence=[latest.get("evidence_ref")],
            check_next="Known pending request/event or bounded local retry",
            scenario_id=scenario_id,
        )
    return _inspection(
        claim,
        "PASS",
        "settlement.stable",
        "The action reached a bounded stable observation boundary.",
        observed=latest.get("settlement_reason"),
        expected="Settled action boundary",
        evidence=[latest.get("evidence_ref")],
        scenario_id=scenario_id,
    )


def _source_payloads(
    evidence: dict[str, list[dict[str, Any]]], event_name: str | None
) -> tuple[list[Any], list[str], bool]:
    payloads: list[Any] = []
    refs: list[str] = []
    direct_complete = _source_windows_complete(evidence)
    for row in evidence["source_calls"]:
        call_time = row.get("capture_mode") == "call_time" and row.get("document_start") is True
        preview_api = (
            row.get("capture_mode") == "preview_api_call" and row.get("authoritative") is True
        )
        if not (call_time or preview_api):
            continue
        for argument in row.get("arguments", []):
            if not isinstance(argument, dict):
                continue
            if event_name is None or argument.get("event") == event_name:
                payloads.append(argument)
                refs.append(row.get("evidence_ref"))
        direct_complete = direct_complete or row.get("collection_complete") is True
    for signal in evidence["direct_signals"]:
        if signal.get("authoritative") is not True:
            continue
        if event_name is None or signal.get("event_name") == event_name:
            payloads.append(signal.get("payload", signal.get("value")))
            refs.append(signal.get("evidence_ref"))
        direct_complete = direct_complete or (
            signal.get("collection_complete") is True
            and (
                signal.get("capture_mode") == "call_time"
                or signal.get("event_list_complete") is True
            )
        )
    return payloads, list(dict.fromkeys(refs)), direct_complete


def _source_windows_complete(evidence: dict[str, list[dict[str, Any]]]) -> bool:
    return any(
        window.get("complete") is True
        and window.get("truncated") is not True
        and (
            (window.get("capture_mode") == "call_time" and window.get("document_start") is True)
            or window.get("authoritative_complete") is True
        )
        for window in evidence.get("source_windows", [])
    )


def _acquisition_inspection(
    event: dict[str, Any],
    action: dict[str, Any],
    evidence: dict[str, list[dict[str, Any]]],
    scenario_id: str,
) -> dict[str, Any] | None:
    expected = event.get("journey", {}).get("acquisition")
    required = action.get("fresh_context_required") is True or expected not in (None, "", {})
    if not required:
        return None
    claim = {
        "claim_id": f"{event['event_id']}::ACQUISITION",
        "domain": "reality",
        "target": {"check": "acquisition", "label": "Fresh acquisition context"},
        "predicate": {"operator": "present"},
        "label": "Fresh acquisition context",
    }
    contexts = evidence.get("acquisition_contexts", [])
    if not contexts:
        return _inspection(
            claim,
            "BLOCKED",
            "acquisition.unobserved",
            "The requested fresh acquisition context was not evidenced.",
            expected=expected or "Fresh controlled/natural acquisition",
            check_next="Referrer, landing URL, storage/session state, and navigation method",
            scenario_id=scenario_id,
        )
    context = contexts[-1]
    failures = []
    if context.get("fresh") is not True:
        failures.append("visit was not fresh")
    if str(context.get("method") or "").upper() == "NOT_APPLICABLE":
        failures.append("acquisition method was marked not applicable")
    expected_source = expected.get("source") if isinstance(expected, dict) else expected
    observed_source = context.get("source", context.get("channel"))
    if (
        expected_source not in (None, "")
        and str(expected_source).casefold() != str(observed_source or "").casefold()
    ):
        failures.append("acquisition source differs from the requested source")
    return _inspection(
        claim,
        "FAIL" if failures else "PASS",
        "acquisition.invalid" if failures else "acquisition.proven",
        "; ".join(failures) + "." if failures else "Fresh acquisition was independently evidenced.",
        observed={
            key: context.get(key)
            for key in ("method", "fresh", "source", "channel", "referrer", "landing_url")
        },
        expected=expected or "Fresh controlled/natural acquisition",
        evidence=[context.get("record_id"), *context.get("evidence_refs", [])],
        check_next="Acquisition navigation and fresh-session evidence" if failures else None,
        scenario_id=scenario_id,
    )


def _source_result(
    claim: dict[str, Any],
    evidence: dict[str, list[dict[str, Any]]],
    scenario_id: str,
) -> dict[str, Any]:
    target = claim.get("target", {})
    event_name = target.get("event_name")
    payloads, refs, complete = _source_payloads(evidence, event_name)
    truncated = any(row.get("truncated") is True for row in evidence["source_calls"])
    if target.get("check") == "event_occurrence":
        actual: Any = len(payloads)
    else:
        path = str(target.get("path") or "")
        actual = _path_observations(payloads, path)
    if truncated:
        return _inspection(
            claim,
            "BLOCKED",
            "source.snapshot_truncated",
            "At least one call-time source argument was truncated, so occurrence/value proof is incomplete.",
            observed=actual,
            evidence=refs,
            check_next="Narrow the source capture or inspect the affected call directly",
            scenario_id=scenario_id,
        )
    if not complete and not payloads:
        return _inspection(
            claim,
            "BLOCKED",
            "source.api_call_unavailable",
            "Neither complete call-time capture nor a fully expanded Tag Assistant API Call is attributable.",
            observed="No complete attributable source call",
            evidence=refs,
            check_next="Fully expanded Tag Assistant API Call or conditional call-time recorder",
            scenario_id=scenario_id,
        )
    result = _evaluate_claim_value(actual, claim)
    return _inspection(
        claim,
        result["status"],
        f"source.{result['reason_code']}",
        result["reason"],
        observed=actual,
        evidence=refs,
        check_next="dataLayer producer/direct source" if result["status"] != "PASS" else None,
        scenario_id=scenario_id,
    )


def _preview_matches(
    evidence: dict[str, list[dict[str, Any]]], event_name: str | None
) -> list[dict[str, Any]]:
    if event_name is None:
        return evidence["preview_events"]
    return [
        row
        for row in evidence["preview_events"]
        if str(row.get("event_name", row.get("name")) or "") == str(event_name)
    ]


_TECHNICAL_PREVIEW_NAMES = {
    "consentinitialisation",
    "consentinitialization",
    "consentupdate",
    "containerloaded",
    "domready",
    "initialisation",
    "initialization",
    "message",
    "set",
    "triggergroup",
    "windowloaded",
}


def _technical_preview_name(value: Any) -> bool:
    compact = "".join(character for character in str(value or "").casefold() if character.isalnum())
    cmp_lifecycle = (
        compact.startswith(("didomi", "onetrust", "cookiebot", "cmp")) or "consent" in compact
    )
    return compact.startswith("gtm") or compact in _TECHNICAL_PREVIEW_NAMES or cmp_lifecycle


def _preview_business_boundary(row: dict[str, Any], event_name: str) -> bool:
    arguments = (
        row.get("api_call", {}).get("arguments", [])
        if isinstance(row.get("api_call"), dict)
        else []
    )
    pushed = [
        str(argument.get("event"))
        for argument in arguments
        if isinstance(argument, dict) and argument.get("event")
    ]
    if any(name != event_name and not _technical_preview_name(name) for name in pushed):
        return True
    row_name = str(row.get("event_name", row.get("name")) or "")
    return bool(not pushed and row_name != event_name and not _technical_preview_name(row_name))


def _preview_causal_rows(
    evidence: dict[str, list[dict[str, Any]]], event_name: str | None
) -> list[dict[str, Any]]:
    """Join exact source rows to their bounded technical follow-up rows.

    API Call, accumulated Data Layer, and Variables stay tied to the exact message.
    Tag firing and runtime details may legitimately appear on a following GTM Trigger
    Group, but never across the next business event.
    """
    exact = _preview_matches(evidence, event_name)
    if event_name is None:
        return exact
    all_rows = evidence.get("preview_events", [])
    output: list[dict[str, Any]] = []
    seen: set[str] = set()
    for source in exact:
        source_epoch = str(source.get("epoch") or "")
        source_action = str(source.get("action_id") or "")
        try:
            source_index = int(source.get("index"))
        except (TypeError, ValueError):
            source_index = None
        candidates = sorted(
            (
                row
                for row in all_rows
                if str(row.get("epoch") or "") == source_epoch
                and (
                    not source_action
                    or not row.get("action_id")
                    or str(row.get("action_id")) == source_action
                )
            ),
            key=lambda row: (
                int(row.get("index")) if str(row.get("index") or "").isdigit() else 10**9
            ),
        )
        for row in candidates:
            try:
                row_index = int(row.get("index"))
            except (TypeError, ValueError):
                continue
            if source_index is not None and row_index < source_index:
                continue
            if row is not source and _preview_business_boundary(row, str(event_name)):
                break
            identity = str(row.get("occurrence_id") or f"{source_epoch}:{row_index}")
            if identity not in seen:
                seen.add(identity)
                output.append(row)
    return output


def _preview_complete(rows: list[dict[str, Any]], key: str) -> bool:
    for row in rows:
        completeness = row.get("completeness") if isinstance(row.get("completeness"), dict) else {}
        if completeness.get(key) is True:
            return True
        if key in {"fired_list", "not_fired_set"} and row.get("full_tag_summary") is True:
            return True
        if key == "event_list" and row.get("history_stable") is True:
            return True
    return False


def _find_tag(rows: list[dict[str, Any]], tag_id: str) -> tuple[list[dict[str, Any]], int, bool]:
    details = []
    fired_count = 0
    seen_not_fired = False
    for event in rows:
        fired = event.get("fired_tags", []) if isinstance(event.get("fired_tags"), list) else []
        not_fired = (
            event.get("not_fired_tags", []) if isinstance(event.get("not_fired_tags"), list) else []
        )
        tags = event.get("tags", []) if isinstance(event.get("tags"), list) else []
        fired_count += sum(_tag_identity(tag) == tag_id for tag in fired)
        seen_not_fired = seen_not_fired or any(_tag_identity(tag) == tag_id for tag in not_fired)
        details.extend(
            tag for tag in tags if isinstance(tag, dict) and _tag_identity(tag) == tag_id
        )
    if details:
        explicit_count = sum(
            int(tag.get("firing_count") or 0) for tag in details if tag.get("fired") is True
        )
        fired_count = max(fired_count, explicit_count)
    return details, fired_count, seen_not_fired


def _concerned_tag_ids(rows: list[dict[str, Any]], target: dict[str, Any]) -> list[str]:
    tag_id = str(target.get("tag_id") or "")
    if tag_id:
        return [tag_id]
    scopes = target.get("tag_scope", [])
    output = []
    for event in rows:
        for tag in event.get("tags", []):
            if isinstance(tag, dict) and _tag_matches_scope(tag, scopes):
                identity = _tag_identity(tag)
                if identity and identity not in output:
                    output.append(identity)
    return output


def _find_concerned_tags(
    rows: list[dict[str, Any]], target: dict[str, Any]
) -> tuple[list[dict[str, Any]], int, bool, list[str]]:
    identities = _concerned_tag_ids(rows, target)
    details: list[dict[str, Any]] = []
    fired_count = 0
    seen_not_fired = False
    for identity in identities:
        found, count, not_fired = _find_tag(rows, identity)
        details.extend(found)
        fired_count += count
        seen_not_fired = seen_not_fired or not_fired
    return details, fired_count, seen_not_fired, identities


def _tag_identity(value: Any) -> str:
    if not isinstance(value, dict):
        return str(value)
    return str(
        value.get("tag_id") or value.get("id") or value.get("tag_name") or value.get("name") or ""
    )


def _preview_static_identity(row: dict[str, Any]) -> tuple[tuple[str, ...], str] | None:
    containers = tuple(sorted(str(value) for value in row.get("container_ids", []) if value))
    workspace_version = str(row.get("workspace_version") or "")
    if not containers or not workspace_version:
        return None
    return containers, workspace_version


def _cached_tag_configuration(
    model: dict[str, Any], rows: list[dict[str, Any]], tag_id: str
) -> tuple[Any, list[Any], bool]:
    identities = {
        identity for row in rows if (identity := _preview_static_identity(row)) is not None
    }
    if len(identities) != 1:
        return MISSING, [], False
    identity = next(iter(identities))
    candidates: list[tuple[Any, list[Any]]] = []
    for row in model.get("preview_events", []):
        if _preview_static_identity(row) != identity:
            continue
        for tag in row.get("tags", []):
            if not isinstance(tag, dict) or _tag_identity(tag) != tag_id:
                continue
            configuration = tag.get("configuration", MISSING)
            if configuration is not MISSING and configuration is not None:
                candidates.append((configuration, row.get("evidence_refs", [])))
    if not candidates:
        return MISSING, [], False
    canonical = {canonical_json(configuration) for configuration, _ in candidates}
    if len(canonical) != 1:
        return MISSING, [ref for _, refs in candidates for ref in refs], True
    return candidates[-1][0], [ref for _, refs in candidates for ref in refs], False


def _tag_matches_scope(tag: Any, scopes: list[Any]) -> bool:
    if not isinstance(tag, dict):
        searchable = str(tag).casefold()
    else:
        searchable = " ".join(
            str(tag.get(key) or "") for key in ("category", "tag_name", "name", "tag_id", "id")
        ).casefold()
    aliases = {
        "ga4": ("ga4", "google analytics"),
        "google ads": ("google ads", "adwords"),
    }
    return any(
        any(
            alias in searchable
            for alias in aliases.get(str(scope).casefold(), (str(scope).casefold(),))
        )
        for scope in scopes
        if str(scope).strip()
    )


def _gtm_missing_result(
    claim: dict[str, Any],
    model: dict[str, Any],
    evidence: dict[str, list[dict[str, Any]]],
    check: Any,
    scenario_id: str,
) -> dict[str, Any]:
    complete = _evidence_collection_complete(evidence, "preview")
    if check == "event_match" and complete:
        result = evaluate_predicate(0, claim.get("predicate", {}))
        return _inspection(
            claim,
            result["status"],
            f"gtm.{result['reason_code']}",
            result["reason"],
            observed=0,
            check_next="Current Tag Assistant event list" if result["status"] != "PASS" else None,
            scenario_id=scenario_id,
        )
    status = "FAIL" if complete else "BLOCKED"
    capability = _capability(model, "preview_events")
    reason = (
        "No matching Preview occurrence was observed in a complete event list."
        if complete
        else "Preview occurrence evidence is unavailable or incomplete"
        + (" because the surface is unsupported." if capability is False else ".")
    )
    return _inspection(
        claim,
        status,
        "gtm.event_missing" if complete else "gtm.preview_unavailable",
        reason,
        observed=0,
        check_next="Current Tag Assistant event list and Preview linkage",
        scenario_id=scenario_id,
    )


def _gtm_inventory_result(
    claim: dict[str, Any], rows: list[dict[str, Any]], refs: list[Any], scenario_id: str
) -> dict[str, Any]:
    complete = _preview_complete(rows, "fired_list") and _preview_complete(rows, "not_fired_set")
    return _inspection(
        claim,
        "PASS" if complete else "BLOCKED",
        "gtm.inventory_complete" if complete else "gtm.inventory_partial",
        (
            "Complete fired and relevant non-fired inventory captured."
            if complete
            else "Preview tag inventory is partial."
        ),
        observed={"events": len(rows), "complete": complete},
        expected="Complete fired and relevant non-fired inventory",
        evidence=refs,
        check_next="Tag Assistant fired/not-fired summary" if not complete else None,
        scenario_id=scenario_id,
    )


def _gtm_discovery_result(
    claim: dict[str, Any], rows: list[dict[str, Any]], refs: list[Any], scenario_id: str
) -> dict[str, Any]:
    scopes = claim.get("target", {}).get("tag_scope", [])
    candidates_by_id: dict[str, dict[str, Any]] = {}
    for event_row in rows:
        for tag in event_row.get("tags", []):
            if _tag_matches_scope(tag, scopes):
                identity = _tag_identity(tag)
                if not identity:
                    continue
                candidates_by_id[identity] = {
                    "tag_id": identity,
                    "category": tag.get("category") if isinstance(tag, dict) else None,
                    "fired": tag.get("fired") if isinstance(tag, dict) else None,
                    "configuration": (tag.get("configuration") if isinstance(tag, dict) else None),
                }
    candidates = list(candidates_by_id.values())
    complete = _preview_complete(rows, "tag_details")
    if not complete:
        status, reason = "BLOCKED", "Runtime tag discovery is incomplete."
    elif not candidates:
        status, reason = "FAIL", "No runtime tag matches the explicitly requested tag scope."
    else:
        status = "PASS"
        reason = "Every concerned runtime tag was identified inside the accepted tag category."
    return _inspection(
        claim,
        status,
        f"gtm.discovery.{status.casefold()}",
        reason,
        observed=candidates,
        expected={"tag_scope": scopes, "identity": "identified concerned runtime tags"},
        evidence=refs,
        check_next=("Current concerned runtime tags and routing" if status != "PASS" else None),
        scenario_id=scenario_id,
    )


def _gtm_firing_result(
    claim: dict[str, Any],
    rows: list[dict[str, Any]],
    refs: list[Any],
    tag_id: str,
    fired_count: int,
    seen_not_fired: bool,
    scenario_id: str,
) -> dict[str, Any]:
    complete = _preview_complete(rows, "fired_list") and _preview_complete(rows, "not_fired_set")
    if not complete:
        return _inspection(
            claim,
            "BLOCKED",
            "gtm.firing_inventory_partial",
            "Tag firing cannot be certified from a partial fired/non-fired inventory.",
            observed={"fired_count": fired_count, "seen_not_fired": seen_not_fired},
            evidence=refs,
            check_next=f"Tag Assistant summary for {tag_id}",
            scenario_id=scenario_id,
        )
    result = evaluate_predicate(fired_count, claim.get("predicate", {}))
    return _inspection(
        claim,
        result["status"],
        f"gtm.firing.{result['reason_code']}",
        result["reason"],
        observed=fired_count,
        evidence=refs,
        check_next=(
            f"GTM trigger/exception/consent for {tag_id}" if result["status"] != "PASS" else None
        ),
        scenario_id=scenario_id,
    )


def _gtm_configuration_result(
    claim: dict[str, Any],
    rows: list[dict[str, Any]],
    refs: list[Any],
    details: list[dict[str, Any]],
    tag_id: str,
    scenario_id: str,
    cached_configuration: Any = MISSING,
    cached_refs: list[Any] | None = None,
    cache_conflict: bool = False,
) -> dict[str, Any]:
    if cache_conflict:
        return _inspection(
            claim,
            "BLOCKED",
            "gtm.configuration_cache_conflict",
            "Static configuration evidence conflicts under the same container/workspace identity.",
            evidence=[*refs, *(cached_refs or [])],
            check_next=f"Current tag configuration for {tag_id}",
            scenario_id=scenario_id,
        )
    if not details and cached_configuration is MISSING:
        status = "FAIL" if _preview_complete(rows, "tag_details") else "BLOCKED"
        return _inspection(
            claim,
            status,
            "gtm.configuration_missing" if status == "FAIL" else "gtm.configuration_unobserved",
            (
                "Expected tag configuration is absent."
                if status == "FAIL"
                else "Expected tag detail was not completely extracted."
            ),
            observed=None,
            evidence=refs,
            check_next=f"Static/detail configuration for {tag_id}",
            scenario_id=scenario_id,
        )
    current_configuration = details[-1].get("configuration") if details else None
    reused = current_configuration is None and cached_configuration is not MISSING
    configuration = cached_configuration if reused else current_configuration
    expected = claim.get("target", {}).get("tag", {}).get("configuration")
    if configuration is None:
        status, reason = "BLOCKED", "Static tag configuration was not extracted."
    elif expected is not None and configuration != expected:
        status, reason = "FAIL", "Observed static tag configuration differs from the plan."
    else:
        status, reason = "PASS", "Static tag configuration is available and coherent."
    reason_code = {
        "PASS": "gtm.configuration_match",
        "FAIL": "gtm.configuration_mismatch",
        "BLOCKED": "gtm.configuration_unobserved",
    }[status]
    return _inspection(
        claim,
        status,
        reason_code,
        reason,
        observed={"configuration": configuration, "reused_static": True}
        if reused
        else configuration,
        expected=expected if expected is not None else "Current in-scope configuration",
        evidence=[*refs, *(cached_refs or [])] if reused else refs,
        check_next=f"Tag configuration for {tag_id}" if status != "PASS" else None,
        scenario_id=scenario_id,
    )


def _gtm_variable_result(
    claim: dict[str, Any], rows: list[dict[str, Any]], refs: list[Any], scenario_id: str
) -> dict[str, Any]:
    path = str(claim.get("target", {}).get("path"))
    actual = _path_observations([row.get("resolved_state", {}) for row in rows], path)
    if actual is MISSING and not _preview_complete(rows, "variables"):
        return _inspection(
            claim,
            "BLOCKED",
            "gtm.variables_partial",
            "Required resolved variable evidence was not completely extracted.",
            check_next=f"Resolved variable {path}",
            evidence=refs,
            scenario_id=scenario_id,
        )
    result = _evaluate_claim_value(actual, claim)
    return _inspection(
        claim,
        result["status"],
        f"gtm.variable.{result['reason_code']}",
        result["reason"],
        observed=actual,
        evidence=refs,
        check_next=f"GTM variable {path}" if result["status"] != "PASS" else None,
        scenario_id=scenario_id,
    )


def _gtm_data_layer_state_result(
    claim: dict[str, Any], rows: list[dict[str, Any]], refs: list[Any], scenario_id: str
) -> dict[str, Any]:
    path = str(claim.get("target", {}).get("path") or "")
    actual = _path_observations([row.get("data_layer_state", {}) for row in rows], path)
    complete = _preview_complete(rows, "data_layer_state")
    if actual is MISSING and not complete:
        return _inspection(
            claim,
            "BLOCKED",
            "gtm.data_layer_state_partial",
            "The Tag Assistant Data Layer state after the selected message was not completely extracted.",
            check_next=f"Tag Assistant Data Layer tab value {path}",
            evidence=refs,
            scenario_id=scenario_id,
        )
    result = _evaluate_claim_value(actual, claim)
    return _inspection(
        claim,
        result["status"],
        f"gtm.data_layer_state.{result['reason_code']}",
        result["reason"],
        observed=actual,
        evidence=refs,
        check_next=f"Tag Assistant Data Layer tab value {path}"
        if result["status"] != "PASS"
        else None,
        scenario_id=scenario_id,
    )


def _configuration_mentions_path(value: Any, path: str) -> bool:
    normalized_path = path.casefold()
    leaf = normalized_path.rsplit(".", 1)[-1].replace("[]", "")
    if isinstance(value, dict):
        for key, child in value.items():
            normalized_key = str(key).casefold()
            if normalized_key in {normalized_path, leaf}:
                return True
            if _configuration_mentions_path(child, path):
                return True
        return False
    if isinstance(value, list):
        return any(_configuration_mentions_path(child, path) for child in value)
    if isinstance(value, str):
        normalized = value.casefold()
        return normalized_path in normalized or leaf == normalized.strip("{} ")
    if path.startswith("ecommerce.") and value is True:
        return False
    return False


def _effective_mapping_result(
    claim: dict[str, Any],
    rows: list[dict[str, Any]],
    refs: list[Any],
    details: list[dict[str, Any]],
    tag_ids: list[str],
    scenario_id: str,
) -> dict[str, Any]:
    path = str(claim.get("target", {}).get("path") or "")
    candidates = [path]
    if path == "event":
        candidates.append("event_name")
    if path.startswith("ecommerce."):
        candidates.append(path.removeprefix("ecommerce."))
    direct = [
        _tag_identity(tag)
        for tag in details
        if _configuration_mentions_path(tag.get("configuration"), path)
    ]
    runtime = []
    for tag in details:
        payload = tag.get("runtime_parameters", tag.get("runtime_payload", {}))
        if any(path_values(payload, candidate) for candidate in candidates):
            runtime.append(_tag_identity(tag))
    covered = list(dict.fromkeys([*direct, *runtime]))
    if covered:
        return _inspection(
            claim,
            "PASS",
            "gtm.effective_mapping_proven",
            "The concerned tag's direct or effective object/settings mapping resolves this planned parameter.",
            observed={
                "covered_by_tags": covered,
                "direct_configuration": direct,
                "runtime": runtime,
            },
            expected={"path": path, "concerned_tags": tag_ids},
            evidence=refs,
            scenario_id=scenario_id,
        )
    complete = _preview_complete(rows, "tag_details") and (
        _preview_complete(rows, "runtime_parameters")
        or any(tag.get("runtime_complete") is True for tag in details)
    )
    return _inspection(
        claim,
        "FAIL" if complete else "BLOCKED",
        "gtm.effective_mapping_absent" if complete else "gtm.effective_mapping_partial",
        (
            "No direct, object/settings, automatic, or runtime mapping covers the planned parameter."
            if complete
            else "Effective tag mapping evidence is incomplete."
        ),
        observed={"concerned_tags": tag_ids, "path": path},
        expected="Effective mapping for every destination-applicable planned parameter",
        evidence=refs,
        check_next=f"Concerned tag mapping/runtime value for {path}",
        scenario_id=scenario_id,
    )


def _gtm_result(
    claim: dict[str, Any],
    evidence: dict[str, list[dict[str, Any]]],
    model: dict[str, Any],
    scenario_id: str,
) -> dict[str, Any]:
    target = claim.get("target", {})
    exact_rows = _preview_matches(evidence, target.get("event_name"))
    check = target.get("check")
    if not exact_rows:
        return _gtm_missing_result(claim, model, evidence, check, scenario_id)

    rows = (
        exact_rows
        if check in {"event_match", "resolved_variable", "data_layer_state"}
        else _preview_causal_rows(evidence, target.get("event_name"))
    )

    refs = [ref for row in rows for ref in row.get("evidence_refs", [])]
    if check == "event_match":
        result = evaluate_predicate(len(rows), claim.get("predicate", {}))
        return _inspection(
            claim,
            result["status"],
            f"gtm.{result['reason_code']}",
            result["reason"],
            observed=len(rows),
            evidence=refs,
            check_next="Matching Preview event occurrence" if result["status"] != "PASS" else None,
            scenario_id=scenario_id,
        )
    if check == "tag_inventory":
        return _gtm_inventory_result(claim, rows, refs, scenario_id)
    if check == "in_scope_tag_discovery":
        return _gtm_discovery_result(claim, rows, refs, scenario_id)

    tag_id = str(target.get("tag_id") or "")
    details, fired_count, seen_not_fired, tag_ids = _find_concerned_tags(rows, target)
    display_tag = tag_id or ", ".join(tag_ids) or "runtime-discovered in-scope tag"
    if check == "tag_firing":
        return _gtm_firing_result(
            claim, rows, refs, display_tag, fired_count, seen_not_fired, scenario_id
        )
    if check == "tag_configuration":
        if not tag_ids:
            return _gtm_missing_result(claim, model, evidence, check, scenario_id)
        if not tag_id and len(tag_ids) > 1:
            configuration_values = [tag.get("configuration") for tag in details]
            if any(value is None for value in configuration_values):
                return _inspection(
                    claim,
                    "BLOCKED",
                    "gtm.dynamic_tag_configuration_partial",
                    "Multiple concerned runtime tags were found and at least one configuration is incomplete.",
                    observed=tag_ids,
                    evidence=refs,
                    check_next="Concerned in-scope tag configurations",
                    scenario_id=scenario_id,
                )
            return _inspection(
                claim,
                "PASS",
                "gtm.dynamic_tag_configurations_complete",
                "Every concerned runtime tag has a complete effective configuration.",
                observed=[
                    {
                        "tag_id": _tag_identity(tag),
                        "configuration": tag.get("configuration"),
                    }
                    for tag in details
                ],
                expected="Complete configuration for every concerned in-scope tag",
                evidence=refs,
                scenario_id=scenario_id,
            )
        cache_tag_id = tag_id or (tag_ids[0] if len(tag_ids) == 1 else "")
        cached, cached_refs, conflict = _cached_tag_configuration(model, rows, cache_tag_id)
        return _gtm_configuration_result(
            claim,
            rows,
            refs,
            details,
            display_tag,
            scenario_id,
            cached,
            cached_refs,
            conflict,
        )
    if check == "resolved_variable":
        return _gtm_variable_result(claim, rows, refs, scenario_id)
    if check == "data_layer_state":
        return _gtm_data_layer_state_result(claim, rows, refs, scenario_id)
    if check == "effective_mapping":
        return _effective_mapping_result(claim, rows, refs, details, tag_ids, scenario_id)
    return _inspection(
        claim,
        "BLOCKED",
        "gtm.check_unknown",
        f"Unsupported GTM check '{check}'.",
        evidence=refs,
        scenario_id=scenario_id,
    )


def _destination_matches(expected: Any, observed: Any) -> bool:
    if expected in (None, ""):
        return True
    return str(expected).strip().casefold() == str(observed or "").strip().casefold()


def _destination_in_scope(target: dict[str, Any], observed: Any) -> bool:
    expected = target.get("destination") or target.get("tag", {}).get("destination")
    if expected not in (None, ""):
        return _destination_matches(expected, observed)
    allowlist = [
        str(value).strip().casefold()
        for value in target.get("destination_allowlist", [])
        if str(value).strip()
    ]
    if allowlist:
        return str(observed or "").strip().casefold() in allowlist
    return True


def _delivery_candidates(
    evidence: dict[str, list[dict[str, Any]]], target: dict[str, Any]
) -> list[dict[str, Any]]:
    event_name = target.get("event_name")
    protocol = target.get("protocol")
    tag_id = str(target.get("tag_id") or "")
    output = []
    for send in evidence["logical_sends"]:
        if protocol and send.get("protocol") != protocol:
            continue
        if event_name and send.get("event_name") != event_name:
            continue
        if not _destination_in_scope(target, send.get("destination")):
            continue
        linked_tags = {str(item) for item in send.get("tag_ids", [])}
        if tag_id and linked_tags and tag_id not in linked_tags:
            continue
        output.append(send)
    return output


def _runtime_parameter_result(
    claim: dict[str, Any],
    evidence: dict[str, list[dict[str, Any]]],
    scenario_id: str,
) -> dict[str, Any]:
    target = claim.get("target", {})
    rows = _preview_causal_rows(evidence, target.get("event_name"))
    tag_id = str(target.get("tag_id") or "")
    details, fired_count, _, tag_ids = _find_concerned_tags(rows, target)
    display_tag = tag_id or ", ".join(tag_ids) or "runtime-discovered in-scope tag"
    refs = [ref for row in rows for ref in row.get("evidence_refs", [])]
    if fired_count == 0:
        return _inspection(
            claim,
            "BLOCKED",
            "delivery.runtime_not_created",
            "The tag did not execute, so runtime parameters were not created.",
            observed="not observed",
            evidence=refs,
            check_next=f"Tag firing and runtime mapping for {display_tag}",
            scenario_id=scenario_id,
        )
    path = str(target.get("path") or "")
    candidates = [path]
    if path == "event":
        candidates.append("event_name")
    if path.startswith("ecommerce."):
        candidates.append(path.removeprefix("ecommerce."))
    values = []
    for tag in details:
        runtime = tag.get("runtime_parameters", tag.get("runtime_payload", {}))
        for candidate in candidates:
            candidate_values = path_values(runtime, candidate)
            if candidate_values:
                values.extend(candidate_values)
                break
    actual = values if ("[]" in path or "[*]" in path) and values else _one_or_distinct(values)
    if actual is MISSING:
        runtime_complete = _preview_complete(rows, "runtime_parameters") or any(
            tag.get("runtime_complete") is True for tag in details
        )
        return _inspection(
            claim,
            "FAIL" if runtime_complete else "BLOCKED",
            "delivery.runtime_parameter_absent" if runtime_complete else "delivery.runtime_partial",
            (
                "The tag executed but the required runtime parameter is absent."
                if runtime_complete
                else "Runtime parameter detail was not completely observed."
            ),
            check_next=f"Runtime parameter {path} for {display_tag}",
            evidence=refs,
            scenario_id=scenario_id,
        )
    result = _evaluate_claim_value(actual, claim)
    return _inspection(
        claim,
        result["status"],
        f"delivery.runtime.{result['reason_code']}",
        result["reason"],
        observed=actual,
        evidence=refs,
        check_next=f"Runtime parameter mapping {path}" if result["status"] != "PASS" else None,
        scenario_id=scenario_id,
    )


def _request_parameter_result(
    claim: dict[str, Any],
    sends: list[dict[str, Any]],
    evidence: dict[str, list[dict[str, Any]]],
    scenario_id: str,
) -> dict[str, Any]:
    target = claim.get("target", {})
    path = str(target.get("path") or "")
    refs = [send.get("evidence_ref") for send in sends]
    actual = _path_observations([send.get("parameters", {}) for send in sends], path)
    complete = _evidence_collection_complete(evidence, "network")
    parameter_complete = any(
        row.get("parameter_capture_complete") is True for row in evidence.get("network_windows", [])
    )
    if actual is MISSING and (not complete or not parameter_complete):
        return _inspection(
            claim,
            "BLOCKED",
            "delivery.network_parameter_partial",
            "The transport window or decoded parameter evidence is incomplete.",
            check_next=f"Request parameter {path}",
            evidence=refs,
            scenario_id=scenario_id,
        )
    result = _evaluate_claim_value(actual, claim, wire=True)
    return _inspection(
        claim,
        result["status"],
        f"delivery.request_parameter.{result['reason_code']}",
        result["reason"],
        observed=actual,
        evidence=refs,
        check_next=f"Browser request parameter {path}" if result["status"] != "PASS" else None,
        scenario_id=scenario_id,
    )


def _attribute_tag_sends(
    target: dict[str, Any], sends: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    tag_id = str(target.get("tag_id") or "")
    linked = [send for send in sends if tag_id in {str(item) for item in send.get("tag_ids", [])}]
    if linked:
        return linked
    has_anchor = bool(
        target.get("destination") or target.get("protocol") or target.get("event_name")
    )
    return sends if has_anchor else []


def _transport_failure_result(
    claim: dict[str, Any],
    sends: list[dict[str, Any]],
    refs: list[Any],
    scenario_id: str,
) -> dict[str, Any] | None:
    failed = [
        send
        for send in sends
        if str(send.get("outcome") or "").casefold() in {"failed", "blocked", "aborted"}
    ]
    if not failed:
        return None

    def successful_status(send: dict[str, Any]) -> bool:
        try:
            status = int(send.get("response_status"))
        except (TypeError, ValueError):
            return False
        return 200 <= status < 400

    contradictory = [send for send in failed if successful_status(send)]
    hard_failed = [send for send in failed if send not in contradictory]
    if not hard_failed:
        return _inspection(
            claim,
            "REVIEW",
            "delivery.transport_conflicting_outcome",
            "The browser reported a failed/aborted outcome but also a successful response status.",
            observed=[
                {
                    "request_id": send.get("request_id"),
                    "outcome": send.get("outcome"),
                    "response_status": send.get("response_status"),
                }
                for send in contradictory
            ],
            expected="One coherent browser transport outcome",
            evidence=refs,
            check_next="Browser request lifecycle and response status",
            scenario_id=scenario_id,
        )
    return _inspection(
        claim,
        "FAIL",
        "delivery.transport_failed",
        "A matching logical send was attempted but its browser transport failed.",
        observed=[
            {
                "request_id": send.get("request_id"),
                "outcome": send.get("outcome"),
                "response_status": send.get("response_status"),
                "failure_reason": send.get("failure_reason"),
            }
            for send in hard_failed
        ],
        expected="Initiated/settled browser transport",
        evidence=refs,
        check_next="Browser request failure/block reason",
        scenario_id=scenario_id,
    )


def _shared_send_result(
    claim: dict[str, Any],
    target: dict[str, Any],
    sends: list[dict[str, Any]],
    evidence: dict[str, list[dict[str, Any]]],
    event: dict[str, Any],
    complete: bool,
    refs: list[Any],
    scenario_id: str,
) -> dict[str, Any] | None:
    if target.get("check") != "tag_request" or not sends:
        return None
    destination = target.get("destination") or target.get("tag", {}).get("destination")
    competing = [
        tag
        for tag in event.get("tags", [])
        if tag.get("expected") == "fire"
        and (
            _destination_matches(destination, tag.get("destination"))
            if destination not in (None, "")
            else _destination_in_scope(target, tag.get("destination"))
        )
        and tag.get("browser_send_required") is not False
    ]
    linked = any(
        str(target.get("tag_id")) in {str(item) for item in send.get("tag_ids", [])}
        for send in sends
    )
    all_target_sends = _delivery_candidates(evidence, {**target, "tag_id": ""})
    insufficient = len(competing) > len(all_target_sends)
    if not insufficient and (len(competing) <= 1 or linked):
        return None
    return _inspection(
        claim,
        "FAIL" if insufficient and complete else "BLOCKED",
        "delivery.shared_send_insufficient"
        if insufficient
        else "delivery.shared_send_unattributed",
        (
            "Fewer logical sends were observed than expected sending tags."
            if insufficient
            else "Shared-destination sends cannot be assigned to each expected tag."
        ),
        observed={
            "logical_sends": len(all_target_sends),
            "tag_attributable_sends": len(sends),
            "expected_tags": [tag["tag_id"] for tag in competing],
        },
        expected="One attributable logical send per expected sending tag",
        evidence=refs,
        check_next="Per-tag request identity/runtime send mapping",
        scenario_id=scenario_id,
    )


def _delivery_result(
    claim: dict[str, Any],
    evidence: dict[str, list[dict[str, Any]]],
    event: dict[str, Any],
    scenario_id: str,
) -> dict[str, Any]:
    target = claim.get("target", {})
    check = target.get("check")
    if check == "runtime_parameter":
        return _runtime_parameter_result(claim, evidence, scenario_id)

    sends = _delivery_candidates(evidence, target)
    if check == "request_parameter":
        return _request_parameter_result(claim, sends, evidence, scenario_id)
    if check == "tag_request" and sends:
        sends = _attribute_tag_sends(target, sends)

    refs = [send.get("evidence_ref") for send in sends]
    complete = _evidence_collection_complete(evidence, "network")
    count = len(sends)
    if not complete and count == 0:
        return _inspection(
            claim,
            "BLOCKED",
            "delivery.network_unavailable",
            "No complete attributable browser transport window is available.",
            observed=0,
            evidence=refs,
            check_next="Continuous browser request capture",
            scenario_id=scenario_id,
        )

    result = evaluate_predicate(count, claim.get("predicate", {}))
    if result["status"] == "PASS":
        failure = _transport_failure_result(claim, sends, refs, scenario_id)
        if failure is not None:
            return failure
    shared = _shared_send_result(claim, target, sends, evidence, event, complete, refs, scenario_id)
    if shared is not None:
        return shared
    observed = [
        {
            "request_id": send.get("request_id"),
            "protocol": send.get("protocol"),
            "event_name": send.get("event_name"),
            "destination": send.get("destination"),
            "outcome": send.get("outcome"),
        }
        for send in sends
    ]
    return _inspection(
        claim,
        result["status"],
        f"delivery.{result['reason_code']}",
        result["reason"],
        observed=observed if observed else 0,
        evidence=refs,
        check_next=(
            "Browser request, destination, and upstream runtime mapping"
            if result["status"] != "PASS"
            else None
        ),
        scenario_id=scenario_id,
    )


def _event_payloads(
    evidence: dict[str, list[dict[str, Any]]], event_name: str | None
) -> list[dict[str, Any]]:
    payloads, _, _ = _source_payloads(evidence, event_name)
    return [payload for payload in payloads if isinstance(payload, dict)]


def _item_business_anomalies(
    event_name: str, business: dict[str, Any], payload: dict[str, Any]
) -> list[dict[str, Any]]:
    anomalies: list[dict[str, Any]] = []
    if event_name in {"view_item", "select_item"}:
        visible = business.get("item_id", business.get("product_id"))
        tracked = path_value(payload, "ecommerce.items[0].item_id")
        if visible not in (None, "") and tracked is not MISSING and str(visible) != str(tracked):
            anomalies.append(
                {
                    "status": "FAIL",
                    "code": "business.stale_item",
                    "reason": "Tracking describes a different item than the visible item.",
                    "observed": {"visible": visible, "tracked": tracked},
                }
            )
    if event_name == "view_item_list":
        visible_ids = business.get("item_ids")
        tracked_items = path_value(payload, "ecommerce.items")
        if isinstance(visible_ids, list) and isinstance(tracked_items, list):
            tracked_ids = [item.get("item_id") for item in tracked_items if isinstance(item, dict)]
            if visible_ids and not set(map(str, visible_ids)).intersection(map(str, tracked_ids)):
                anomalies.append(
                    {
                        "status": "FAIL",
                        "code": "business.stale_item_list",
                        "reason": "Tracked list items do not describe any currently visible item.",
                        "observed": {"visible": visible_ids, "tracked": tracked_ids},
                    }
                )
    return anomalies


def _completion_business_anomalies(
    event_name: str,
    after: dict[str, Any] | None,
    payloads: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    completion = after.get("completion", {}) if isinstance(after, dict) else {}
    if event_name == "purchase" and (
        not isinstance(completion, dict) or completion.get("confirmed") is not True
    ):
        return [
            {
                "status": "FAIL",
                "code": "business.purchase_unconfirmed",
                "reason": "Purchase tracking was observed without independent confirmation.",
                "observed": completion,
            }
        ]
    if (
        ("form" in event_name or event_name in {"generate_lead", "sign_up"})
        and payloads
        and (not isinstance(completion, dict) or completion.get("succeeded") is not True)
    ):
        return [
            {
                "status": "FAIL",
                "code": "business.form_success_unproven",
                "reason": "A success event was observed without an independently successful form outcome.",
                "observed": completion,
            }
        ]
    return []


def _cart_business_anomalies(
    event_name: str,
    business: dict[str, Any],
    payload: dict[str, Any],
    before: dict[str, Any] | None,
    after: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    anomalies: list[dict[str, Any]] = []
    if event_name == "view_cart":
        item_count = business.get("item_count")
        items = path_value(payload, "ecommerce.items")
        if isinstance(item_count, int) and item_count > 0 and items in (MISSING, None, []):
            anomalies.append(
                {
                    "status": "FAIL",
                    "code": "business.populated_cart_empty_payload",
                    "reason": "The visible cart contains products but tracking has no cart items.",
                    "observed": {
                        "visible_item_count": item_count,
                        "tracked_items": _summary(items),
                    },
                }
            )
    if not before or not after or event_name not in {"add_to_cart", "remove_from_cart"}:
        return anomalies
    before_count = path_value(before, "business.item_count")
    after_count = path_value(after, "business.item_count")
    if not isinstance(before_count, int) or not isinstance(after_count, int):
        return anomalies
    delta = after_count - before_count
    expected_sign = 1 if event_name == "add_to_cart" else -1
    if delta * expected_sign <= 0:
        anomalies.append(
            {
                "status": "FAIL",
                "code": "business.cart_delta_wrong",
                "reason": "Visible cart state moved in the wrong direction for the tracked action.",
                "observed": {"before": before_count, "after": after_count},
            }
        )
    return anomalies


def _context_business_anomalies(
    event_name: str, business: dict[str, Any], payload: dict[str, Any]
) -> list[dict[str, Any]]:
    contextual_checks = {
        "add_shipping_info": (
            "selected_shipping_tier",
            ("ecommerce.shipping_tier", "shipping_tier"),
        ),
        "add_payment_info": ("selected_payment_type", ("ecommerce.payment_type", "payment_type")),
        "page_view": ("page_language", ("page_language", "language")),
    }
    if event_name not in contextual_checks:
        return []
    business_key, paths = contextual_checks[event_name]
    visible = business.get(business_key)
    tracked = next(
        (
            candidate
            for candidate in (path_value(payload, path) for path in paths)
            if candidate is not MISSING
        ),
        MISSING,
    )
    if (
        visible in (None, "")
        or tracked is MISSING
        or str(visible).casefold() == str(tracked).casefold()
    ):
        return []
    return [
        {
            "status": "FAIL",
            "code": "business.context_value_mismatch",
            "reason": "Tracking does not match the option or context actually selected on the page.",
            "observed": {"visible": visible, "tracked": tracked},
        }
    ]


def _tracked_item_ids(payload: dict[str, Any]) -> list[str]:
    items = path_value(payload, "ecommerce.items")
    if not isinstance(items, list):
        return []
    return [
        str(item["item_id"]) for item in items if isinstance(item, dict) and item.get("item_id")
    ]


def _ecommerce_continuity_anomalies(
    event_name: str, business: dict[str, Any], payload: dict[str, Any]
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    tracked_ids = _tracked_item_ids(payload)
    action_item = business.get("action_item_id")
    if (
        event_name in {"add_to_cart", "remove_from_cart"}
        and action_item not in (None, "")
        and (not tracked_ids or str(action_item) != tracked_ids[0])
    ):
        output.append(
            {
                "status": "FAIL",
                "code": "business.action_item_mismatch",
                "reason": "The ecommerce event does not describe the item actually acted on.",
                "observed": {"action_item": action_item, "tracked_items": tracked_ids},
            }
        )

    continuity_events = {
        "view_cart",
        "begin_checkout",
        "add_shipping_info",
        "add_payment_info",
        "purchase",
    }
    expected_ids = business.get(
        "order_item_ids" if event_name == "purchase" else "cart_item_ids",
        business.get("item_ids"),
    )
    if event_name in continuity_events and isinstance(expected_ids, list) and expected_ids:
        expected_set = set(map(str, expected_ids))
        if not tracked_ids or set(tracked_ids) != expected_set:
            output.append(
                {
                    "status": "FAIL",
                    "code": "business.ecommerce_items_mismatch",
                    "reason": "Tracked ecommerce items do not match the current cart/order state.",
                    "observed": {
                        "business_items": sorted(expected_set),
                        "tracked_items": tracked_ids,
                    },
                }
            )

    if event_name == "purchase":
        expected_transaction = business.get("transaction_id", business.get("order_id"))
        tracked_transaction = path_value(payload, "ecommerce.transaction_id")
        if expected_transaction not in (None, "") and (
            tracked_transaction is MISSING or str(expected_transaction) != str(tracked_transaction)
        ):
            output.append(
                {
                    "status": "FAIL",
                    "code": "business.transaction_mismatch",
                    "reason": "Purchase tracking does not match the independently confirmed transaction.",
                    "observed": {
                        "confirmed_transaction": expected_transaction,
                        "tracked_transaction": _summary(tracked_transaction),
                    },
                }
            )

    expected_currency = business.get("currency")
    tracked_currency = path_value(payload, "ecommerce.currency")
    if expected_currency not in (None, "") and (
        tracked_currency is MISSING
        or str(expected_currency).casefold() != str(tracked_currency).casefold()
    ):
        output.append(
            {
                "status": "FAIL",
                "code": "business.currency_mismatch",
                "reason": "Tracked currency differs from the current business state.",
                "observed": {"business": expected_currency, "tracked": _summary(tracked_currency)},
            }
        )

    expected_value = business.get("tracking_value", business.get("measurement_value"))
    tracked_value = path_value(payload, "ecommerce.value")
    if isinstance(expected_value, (int, float)) and not isinstance(expected_value, bool):
        value_matches = (
            isinstance(tracked_value, (int, float))
            and not isinstance(tracked_value, bool)
            and abs(float(expected_value) - float(tracked_value)) <= 0.01
        )
        if not value_matches:
            output.append(
                {
                    "status": "FAIL",
                    "code": "business.value_mismatch",
                    "reason": "Tracked value differs from the explicitly anchored measurement value.",
                    "observed": {"business": expected_value, "tracked": _summary(tracked_value)},
                }
            )
    return output


def _media_context(business: dict[str, Any]) -> dict[str, Any]:
    if isinstance(business.get("media"), dict):
        return business["media"]
    return {
        key: business[key]
        for key in (
            "player_state",
            "media_title",
            "video_title",
            "progress_percent",
            "completed",
            "started",
            "visible",
            "visibility_required",
        )
        if key in business
    }


def _media_playback_anomalies(lower: str, media: dict[str, Any]) -> list[dict[str, Any]]:
    output = []
    state = str(media.get("player_state") or "").casefold()
    if any(token in lower for token in ("start", "play")) and not (
        media.get("started") is True or state in {"playing", "started"}
    ):
        output.append(
            {
                "status": "FAIL",
                "code": "business.media_start_state_mismatch",
                "reason": "A media start/play event occurred while the player was not started or playing.",
                "observed": media,
            }
        )
    if any(token in lower for token in ("complete", "ended", "finish")) and not (
        media.get("completed") is True or state in {"completed", "ended"}
    ):
        output.append(
            {
                "status": "FAIL",
                "code": "business.media_completion_unproven",
                "reason": "A media completion event occurred before independent completion was observed.",
                "observed": media,
            }
        )
    if "pause" in lower and state != "paused":
        output.append(
            {
                "status": "FAIL",
                "code": "business.media_pause_state_mismatch",
                "reason": "A media pause event occurred while the player was not paused.",
                "observed": media,
            }
        )
    return output


def _media_progress_anomalies(
    lower: str, media: dict[str, Any], payload: dict[str, Any]
) -> list[dict[str, Any]]:
    if "progress" not in lower:
        return []
    visible_percent = media.get("progress_percent")
    tracked_percent = next(
        (
            value
            for value in (
                path_value(payload, "video_percent"),
                path_value(payload, "media.percent"),
                path_value(payload, "percent"),
            )
            if value is not MISSING
        ),
        MISSING,
    )
    if visible_percent is None:
        return [
            {
                "status": "BLOCKED",
                "code": "business.media_progress_unobserved",
                "reason": "Media progress tracking lacks an independent player-progress anchor.",
                "observed": media,
            }
        ]
    matches = (
        isinstance(tracked_percent, (int, float))
        and not isinstance(tracked_percent, bool)
        and abs(float(visible_percent) - float(tracked_percent)) <= 1.0
    )
    if matches:
        return []
    return [
        {
            "status": "FAIL",
            "code": "business.media_progress_mismatch",
            "reason": "Tracked media progress differs from the actual player progress.",
            "observed": {"player": visible_percent, "tracked": _summary(tracked_percent)},
        }
    ]


def _media_identity_anomalies(
    media: dict[str, Any], payload: dict[str, Any]
) -> list[dict[str, Any]]:
    output = []
    visible_title = media.get("media_title", media.get("video_title"))
    tracked_title = next(
        (
            value
            for value in (
                path_value(payload, "video_title"),
                path_value(payload, "media.title"),
                path_value(payload, "media_title"),
            )
            if value is not MISSING
        ),
        MISSING,
    )
    if (
        visible_title not in (None, "")
        and tracked_title is not MISSING
        and str(visible_title) != str(tracked_title)
    ):
        output.append(
            {
                "status": "FAIL",
                "code": "business.media_identity_mismatch",
                "reason": "The media event describes a different player item/title.",
                "observed": {"player": visible_title, "tracked": tracked_title},
            }
        )
    if media.get("visibility_required") is True and media.get("visible") is not True:
        output.append(
            {
                "status": "FAIL",
                "code": "business.media_visibility_mismatch",
                "reason": "The media event occurred outside its declared visible-player condition.",
                "observed": media.get("visible"),
            }
        )
    return output


def _media_business_anomalies(
    event_name: str, business: dict[str, Any], payload: dict[str, Any]
) -> list[dict[str, Any]]:
    lower = event_name.casefold()
    if not any(token in lower for token in ("video", "media", "audio")):
        return []
    media = _media_context(business)
    if not media:
        return [
            {
                "status": "BLOCKED",
                "code": "business.media_state_unobserved",
                "reason": "A media event was observed without an independent player-state anchor.",
                "observed": None,
            }
        ]
    return [
        *_media_playback_anomalies(lower, media),
        *_media_progress_anomalies(lower, media, payload),
        *_media_identity_anomalies(media, payload),
    ]


def _repeated_transaction_anomalies(
    event: dict[str, Any], model: dict[str, Any]
) -> list[dict[str, Any]]:
    if str(event.get("event_name") or "") != "purchase":
        return []
    occurrences: dict[str, list[dict[str, Any]]] = {}
    for row in _authoritative_stream_rows(model.get("source_calls", [])):
        for argument in row.get("arguments", []):
            if not isinstance(argument, dict) or argument.get("event") != "purchase":
                continue
            transaction_id = path_value(argument, "ecommerce.transaction_id")
            if transaction_id in (MISSING, None, ""):
                continue
            occurrences.setdefault(str(transaction_id), []).append(
                {
                    "action_id": row.get("action_id"),
                    "call_index": row.get("call_index"),
                    "evidence_ref": row.get("evidence_ref"),
                }
            )
    duplicates = {key: rows for key, rows in occurrences.items() if len(rows) > 1}
    if not duplicates:
        return []
    return [
        {
            "status": "FAIL",
            "code": "business.repeated_transaction",
            "reason": "The same purchase transaction identifier was emitted more than once.",
            "observed": duplicates,
            "evidence": [row["evidence_ref"] for rows in duplicates.values() for row in rows],
        }
    ]


def _business_anomalies(
    event: dict[str, Any], evidence: dict[str, list[dict[str, Any]]]
) -> list[dict[str, Any]]:
    event_name = str(event.get("event_name") or "")
    pages = evidence["pages"]
    before = next((row for row in pages if row.get("phase") == "before"), None)
    after = next((row for row in reversed(pages) if row.get("phase") == "after"), None)
    payloads = _event_payloads(evidence, event.get("event_name"))
    payload = payloads[-1] if payloads else {}
    business = (
        after.get("business", {})
        if isinstance(after, dict) and isinstance(after.get("business"), dict)
        else {}
    )
    return [
        *_item_business_anomalies(event_name, business, payload),
        *_cart_business_anomalies(event_name, business, payload, before, after),
        *_completion_business_anomalies(event_name, after, payloads),
        *_context_business_anomalies(event_name, business, payload),
        *_ecommerce_continuity_anomalies(event_name, business, payload),
        *_media_business_anomalies(event_name, business, payload),
    ]


def _stream_context(
    event: dict[str, Any], evidence: dict[str, list[dict[str, Any]]], model: dict[str, Any]
) -> tuple[list[str], set[str], set[str], set[str]]:
    source_rows = _authoritative_stream_rows(evidence["source_calls"])
    names = [name for row in source_rows for name in row.get("events", [])]
    names.extend(
        str(row.get("event_name")) for row in evidence["direct_signals"] if row.get("event_name")
    )
    action_ids = {
        str(row.get("action_id"))
        for key in ("pages", "source_calls", "direct_signals", "preview_events")
        for row in evidence[key]
        if row.get("action_id")
    }
    bound_event_ids = {
        str(event_id)
        for action in model.get("actions", [])
        if str(action.get("action_id")) in action_ids
        for event_id in action.get("event_ids", [])
    }
    bound_names = {
        str(candidate.get("event_name"))
        for candidate in model.get("plan_events", [])
        if str(candidate.get("event_id")) in bound_event_ids and candidate.get("event_name")
    }
    allowed = {
        str(event.get("event_name") or ""),
        *bound_names,
        *map(str, event.get("allowed_companions", [])),
    }
    planned = {
        str(candidate.get("event_name"))
        for candidate in model.get("plan_events", [])
        if candidate.get("event_name")
    }
    return names, action_ids, allowed, planned


def _authoritative_stream_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        row
        for row in rows
        if (row.get("capture_mode") == "call_time" and row.get("document_start") is True)
        or (row.get("capture_mode") == "preview_api_call" and row.get("authoritative") is True)
    ]


def _occurrence_anomalies(
    names: list[str], allowed: set[str], planned: set[str]
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    counts = {name: names.count(name) for name in dict.fromkeys(names) if name}
    for name, count in counts.items():
        if count > 1 and not name.startswith("gtm."):
            output.append(
                {
                    "status": "FAIL",
                    "code": "behavior.duplicate",
                    "reason": f"One interaction window emitted {count} {name} occurrences.",
                    "observed": names,
                }
            )
    for name in names:
        if name in allowed or name.startswith("gtm."):
            continue
        output.append(
            {
                "status": "REVIEW" if name not in planned else "FAIL",
                "code": "behavior.unexpected_event",
                "reason": f"Unexpected event '{name}' occurred in the action stream.",
                "observed": names,
            }
        )
    return output


def _interstitial_state_anomalies(
    source_calls: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    material_keys = {
        "ecommerce",
        "items",
        "item_id",
        "currency",
        "value",
        "transaction_id",
        "user_data",
        "page_location",
        "page_language",
    }
    output: list[dict[str, Any]] = []
    for row in source_calls:
        if row.get("action_id") is not None:
            continue
        for argument, classification in zip(
            row.get("arguments", []), row.get("classifications", []), strict=False
        ):
            if classification != "STATE_UPDATE" or not isinstance(argument, dict):
                continue
            touched = sorted(material_keys.intersection(map(str, argument)))
            if touched:
                output.append(
                    {
                        "status": "REVIEW",
                        "code": "behavior.interstitial_state_update",
                        "reason": "A material dataLayer state update occurred between guided interactions.",
                        "observed": {"keys": touched, "call_index": row.get("call_index")},
                        "evidence": [row.get("evidence_ref")],
                    }
                )
    return output


def _source_window_complete(evidence: dict[str, list[dict[str, Any]]]) -> bool:
    return (
        _source_windows_complete(evidence)
        or any(
            (
                (row.get("capture_mode") == "call_time" and row.get("document_start") is True)
                or (
                    row.get("capture_mode") == "preview_api_call"
                    and row.get("authoritative") is True
                )
            )
            and row.get("collection_complete") is True
            and row.get("truncated") is not True
            for row in evidence["source_calls"]
        )
        or any(
            row.get("authoritative") is True
            and row.get("collection_complete") is True
            and (row.get("capture_mode") == "call_time" or row.get("event_list_complete") is True)
            for row in evidence["direct_signals"]
        )
    )


def _cross_surface_anomalies(
    event: dict[str, Any],
    evidence: dict[str, list[dict[str, Any]]],
    model: dict[str, Any],
    names: list[str],
    action_ids: set[str],
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    raw_count = names.count(str(event.get("event_name") or ""))
    preview_count = len(_preview_matches(evidence, event.get("event_name")))
    preview_complete = _evidence_collection_complete(evidence, "preview")
    if _source_window_complete(evidence) and preview_complete and raw_count != preview_count:
        output.append(
            {
                "status": "FAIL",
                "code": "behavior.raw_preview_count_mismatch",
                "reason": "Complete raw-source and Preview occurrence counts differ.",
                "observed": {"raw": raw_count, "preview": preview_count},
            }
        )
    for conflict in model.get("ambiguous", []):
        if conflict.get("action_id") in action_ids or conflict.get("action_id") is None:
            output.append(
                {
                    "status": "BLOCKED",
                    "code": "behavior.identity_conflict",
                    "reason": "A collector identity was reused for incompatible observations.",
                    "observed": conflict,
                }
            )
    for error in evidence["runtime_errors"]:
        output.append(
            {
                "status": "REVIEW",
                "code": "behavior.runtime_error",
                "reason": "A runtime error occurred near the tested action.",
                "observed": error,
                "evidence": [error.get("evidence_ref")],
            }
        )
    return output


def _stream_anomalies(
    event: dict[str, Any], evidence: dict[str, list[dict[str, Any]]], model: dict[str, Any]
) -> list[dict[str, Any]]:
    names, action_ids, allowed, planned = _stream_context(event, evidence, model)
    return [
        *_occurrence_anomalies(names, allowed, planned),
        *_interstitial_state_anomalies(_authoritative_stream_rows(evidence["source_calls"])),
        *_cross_surface_anomalies(event, evidence, model, names, action_ids),
        *_business_anomalies(event, evidence),
        *_repeated_transaction_anomalies(event, model),
    ]


def _behavior_result(
    claim: dict[str, Any],
    evidence: dict[str, list[dict[str, Any]]],
    model: dict[str, Any],
    event: dict[str, Any],
    scenario_id: str,
) -> dict[str, Any]:
    if claim.get("target", {}).get("check") == "order":
        names = []
        for row in _authoritative_stream_rows(evidence["source_calls"]):
            names.extend(row.get("events", []))
        names.extend(
            str(row.get("event_name"))
            for row in evidence["direct_signals"]
            if row.get("event_name")
        )
        result = evaluate_predicate(names, claim.get("predicate", {}))
        return _inspection(
            claim,
            result["status"],
            f"behavior.order.{result['reason_code']}",
            result["reason"],
            observed=names,
            check_next="Chronological call-time event stream"
            if result["status"] != "PASS"
            else None,
            scenario_id=scenario_id,
        )
    anomalies = _stream_anomalies(event, evidence, model)
    refs = [item for anomaly in anomalies for item in anomaly.get("evidence", [])]
    if not anomalies:
        has_continuous_stream = _source_window_complete(evidence)
        if not has_continuous_stream:
            return _inspection(
                claim,
                "BLOCKED",
                "behavior.stream_unavailable",
                "No attributable continuous event stream was available for anomaly inspection.",
                expected="Continuous surrounding source/GTM/runtime observation",
                check_next="Continuous stream capture around the interaction",
                scenario_id=scenario_id,
            )
        return _inspection(
            claim,
            "PASS",
            "behavior.no_anomaly",
            "No material count, sequence, state, or runtime anomaly was detected.",
            observed=source_event_names(
                {
                    **model,
                    "source_calls": evidence["source_calls"],
                    "direct_signals": evidence["direct_signals"],
                },
                authoritative_only=True,
            ),
            expected="Causally coherent surrounding behavior",
            scenario_id=scenario_id,
        )
    status = worst_status(anomaly["status"] for anomaly in anomalies)
    return _inspection(
        claim,
        status,
        anomalies[0]["code"],
        " | ".join(anomaly["reason"] for anomaly in anomalies),
        observed=[anomaly.get("observed") for anomaly in anomalies],
        expected="No duplicate, premature, unexpected, stale, or contradictory behavior",
        evidence=refs,
        check_next="Chronology, source producer, GTM trigger, and affected business state",
        scenario_id=scenario_id,
    )


def _safety_result(
    claim: dict[str, Any],
    model: dict[str, Any],
    evidence: dict[str, list[dict[str, Any]]],
    scenario_id: str,
) -> dict[str, Any]:
    action_refs: set[str] = set()
    for rows in evidence.values():
        for row in rows:
            references = row.get("evidence_refs")
            if not isinstance(references, list):
                references = []
            for reference in [row.get("evidence_ref"), *references]:
                if reference:
                    action_refs.add(str(reference))
    event_name = claim.get("target", {}).get("event_name")
    planned_tags = {str(value) for value in claim.get("target", {}).get("tag_ids", []) if value}
    planned_destinations = {
        str(value) for value in claim.get("target", {}).get("destinations", []) if value
    }
    request_ids = {
        str(send.get("request_id"))
        for send in evidence.get("logical_sends", [])
        if send.get("request_id")
        and (
            (event_name and str(send.get("event_name") or "") == str(event_name))
            or planned_tags.intersection(str(value) for value in send.get("tag_ids", []))
            or str(send.get("destination") or "") in planned_destinations
        )
    }
    findings = [
        item
        for item in model.get("privacy_findings", [])
        if str(item.get("evidence_ref") or "") in action_refs
        and (
            item.get("adapter") != "network"
            or (item.get("request_id") is not None and str(item.get("request_id")) in request_ids)
        )
    ]
    confirmed = [
        item
        for item in findings
        if item.get("status") == "FAIL" or item.get("confidence") == "confirmed"
    ]
    if confirmed:
        return _inspection(
            claim,
            "FAIL",
            "safety.sensitive_data",
            "Sensitive or prohibited data was found in captured measurement evidence.",
            observed=[
                {"path": item.get("path"), "category": item.get("category")} for item in confirmed
            ],
            expected="No prohibited sensitive data",
            evidence=[item.get("evidence_ref") for item in confirmed],
            check_next="Exact redacted source/runtime/request field",
            scenario_id=scenario_id,
        )
    return _inspection(
        claim,
        "PASS",
        "safety.clean",
        "No prohibited sensitive value was retained in captured evidence.",
        observed="No confirmed finding",
        expected="No prohibited sensitive data",
        scenario_id=scenario_id,
    )


def _consent_context(
    event: dict[str, Any], evidence: dict[str, list[dict[str, Any]]]
) -> tuple[list[str], dict[str, list[str]], list[dict[str, Any]], list[dict[str, Any]]]:
    required = [str(item) for item in event.get("required_consent_signals", [])]
    tag_requirements = {
        tag["tag_id"]: [str(item) for item in tag.get("consent_requirements", [])]
        for tag in event.get("tags", [])
        if tag.get("consent_requirements")
    }
    preview_rows = _preview_causal_rows(evidence, event.get("event_name"))
    transitions = [
        row
        for row in evidence["consent_transitions"]
        if isinstance(row.get("state"), dict)
        and str(row.get("kind") or "").casefold()
        in {"initialization", "update", "user_choice", "withdrawal"}
    ]
    return required, tag_requirements, preview_rows, transitions


def _consent_state(
    preview_rows: list[dict[str, Any]], transitions: list[dict[str, Any]]
) -> tuple[dict[str, Any], list[Any]]:
    state: dict[str, Any] = {}
    refs: list[Any] = []
    for transition in transitions:
        state.update(transition.get("state", {}))
        refs.append(transition.get("evidence_ref"))
    for row in preview_rows:
        if isinstance(row.get("consent"), dict):
            state.update(row["consent"])
            refs.extend(row.get("evidence_refs", []))
    return state, refs


def _consent_status_result(
    claim: dict[str, Any],
    required: list[str],
    tag_requirements: dict[str, list[str]],
    state: dict[str, Any],
    refs: list[Any],
    transitions: list[dict[str, Any]],
    scenario_id: str,
) -> dict[str, Any]:
    all_required = list(
        dict.fromkeys(
            [*required, *[signal for values in tag_requirements.values() for signal in values]]
        )
    )
    if not state:
        return _inspection(
            claim,
            "BLOCKED",
            "consent.state_unobserved",
            "Consent is applicable but no authoritative event-time state was observed.",
            observed=None,
            expected=all_required,
            evidence=refs,
            check_next="Tag Assistant consent view and Consent Initialization/Update chronology",
            scenario_id=scenario_id,
        )
    natural = any(
        str(row.get("method") or "natural").casefold() != "override" for row in transitions
    )
    override_only = bool(transitions) and not natural
    missing = [signal for signal in all_required if signal not in state]
    if missing or override_only:
        return _inspection(
            claim,
            "BLOCKED",
            "consent.signal_missing" if missing else "consent.override_only",
            (
                "Required event-time consent signals are missing."
                if missing
                else "Only an override consent state was observed; natural CMP behavior is unproven."
            ),
            observed=state,
            expected=all_required or "Natural event-time consent",
            evidence=refs,
            check_next="Current Preview consent state and natural choice transition",
            scenario_id=scenario_id,
        )
    return _inspection(
        claim,
        "PASS",
        "consent.event_time_observed",
        "Event-time consent was derived from typed Preview/transition evidence.",
        observed=state,
        expected=all_required or "Applicable tag consent state",
        evidence=refs,
        scenario_id=scenario_id,
    )


def _consent_tag_result(
    event: dict[str, Any],
    evidence: dict[str, list[dict[str, Any]]],
    preview_rows: list[dict[str, Any]],
    tag_id: str,
    signals: list[str],
    state: dict[str, Any],
    refs: list[Any],
    scenario_id: str,
) -> dict[str, Any] | None:
    denied = any(
        str(state.get(signal) or "").casefold() in {"denied", "false", "0"} for signal in signals
    )
    _, fired_count, _ = _find_tag(preview_rows, tag_id)
    tag = next((row for row in event.get("tags", []) if row.get("tag_id") == tag_id), {})
    sends = []
    for send in evidence["logical_sends"]:
        linked = {str(item) for item in send.get("tag_ids", [])}
        destination_match = tag.get("destination") not in (None, "") and _destination_matches(
            tag.get("destination"), send.get("destination")
        )
        sole_event_match = len(event.get("tags", [])) == 1 and send.get("event_name") == event.get(
            "event_name"
        )
        if tag_id in linked or destination_match or sole_event_match:
            sends.append(send)
    if not denied or not (fired_count or sends):
        return None
    tag_claim = {
        "claim_id": f"{event['event_id']}::CONSENT::{tag_id}",
        "domain": "gtm",
        "target": {
            "check": "tag_consent",
            "tag_id": tag_id,
            "label": f"Consent behavior - {tag_id}",
        },
        "predicate": {"operator": "absent"},
        "label": f"Consent behavior - {tag_id}",
    }
    return _inspection(
        tag_claim,
        "FAIL",
        "consent.denied_tag_or_send",
        "A consent-dependent tag or send occurred while its required consent was denied.",
        observed={"state": state, "fired_count": fired_count, "send_count": len(sends)},
        expected="No tag execution or browser send under denied consent",
        evidence=[*refs, *[send.get("evidence_ref") for send in sends]],
        check_next=f"Consent settings and trigger for {tag_id}",
        scenario_id=scenario_id,
    )


def _consent_inspections(
    event: dict[str, Any],
    evidence: dict[str, list[dict[str, Any]]],
    scenario_id: str,
) -> list[dict[str, Any]]:
    required, tag_requirements, preview_rows, transitions = _consent_context(event, evidence)
    preview_states = [
        row.get("consent") for row in preview_rows if isinstance(row.get("consent"), dict)
    ]
    if not (required or tag_requirements or preview_states or transitions):
        return []
    claim = {
        "claim_id": f"{event['event_id']}::CONSENT",
        "domain": "gtm",
        "target": {"check": "event_time_consent", "label": "Event-time consent"},
        "predicate": {"operator": "present"},
        "label": "Event-time consent",
    }
    state, refs = _consent_state(preview_rows, transitions)
    output = [
        _consent_status_result(
            claim, required, tag_requirements, state, refs, transitions, scenario_id
        )
    ]
    for tag_id, signals in tag_requirements.items():
        result = _consent_tag_result(
            event, evidence, preview_rows, tag_id, signals, state, refs, scenario_id
        )
        if result is not None:
            output.append(result)
    return output


def _evidence_with_neighbors(
    model: dict[str, Any], action: dict[str, Any]
) -> dict[str, list[dict[str, Any]]]:
    evidence = action_evidence(model, action["action_id"])
    actions = model["actions"]
    index = next(
        (
            position
            for position, row in enumerate(actions)
            if row["action_id"] == action["action_id"]
        ),
        0,
    )
    following = actions[index + 1] if index + 1 < len(actions) else None
    from value_semantics import parse_iso_timestamp

    lower = parse_iso_timestamp(action.get("committed_at"))
    upper = parse_iso_timestamp(following.get("began_at")) if following else None

    def nearby(row: dict[str, Any]) -> bool:
        if row.get("action_id") is not None:
            return False
        timestamp = parse_iso_timestamp(row.get("timestamp", row.get("observed_at")))
        if timestamp is None:
            return False
        return lower is not None and timestamp >= lower and (upper is None or timestamp < upper)

    for key in (
        "source_calls",
        "direct_signals",
        "preview_events",
        "requests",
        "logical_sends",
        "lifecycle_events",
        "runtime_errors",
        "consent_transitions",
    ):
        evidence[key].extend(row for row in model[key] if nearby(row))
    return evidence


def _semantic_annotations(
    records: list[dict[str, Any]], event_id: str, scenario_id: str
) -> list[dict[str, Any]]:
    output = []
    for record in records:
        if record.get("kind") != "SEMANTIC_FINDING":
            continue
        data = record.get("data", {})
        if str(data.get("event_id")) != event_id:
            continue
        if data.get("scenario_id") not in (None, scenario_id):
            continue
        status = str(data.get("status") or "REVIEW").upper()
        if status not in {"FAIL", "REVIEW"}:
            status = "REVIEW"
        output.append(
            {
                "claim_id": f"{event_id}::AI::{record.get('record_id')}",
                "scenario_id": scenario_id,
                "domain": "behavior",
                "inspection_target": str(data.get("target") or "Analyst semantic finding"),
                "status": status,
                "reason_code": str(data.get("reason_code") or "semantic.finding"),
                "reason": compact_reason(data.get("reason") or "Evidence-bound semantic finding."),
                "observed": _summary(data.get("observed")),
                "expected": _summary(data.get("expected")),
                "check_next": data.get("check_next"),
                "evidence": list(map(str, data.get("evidence_refs", []))),
                "target": {"check": "semantic_finding"},
            }
        )
    return output


def _evaluate_claim(
    claim: dict[str, Any],
    evidence: dict[str, list[dict[str, Any]]],
    model: dict[str, Any],
    event: dict[str, Any],
    scenario_id: str,
) -> dict[str, Any]:
    archetype = claim.get("archetype")
    if archetype == "reality":
        return _page_result(claim, evidence, event, scenario_id)
    if archetype == "source":
        return _source_result(claim, evidence, scenario_id)
    if archetype == "gtm":
        return _gtm_result(claim, evidence, model, scenario_id)
    if archetype == "delivery":
        return _delivery_result(claim, evidence, event, scenario_id)
    if archetype == "sequence":
        return _behavior_result(claim, evidence, model, event, scenario_id)
    if archetype == "safety":
        return _safety_result(claim, model, evidence, scenario_id)
    return _inspection(
        claim,
        "BLOCKED",
        "claim.archetype_unknown",
        f"Unsupported claim archetype '{archetype}'.",
        scenario_id=scenario_id,
    )


def _apply_live_plan_gap(
    row: dict[str, Any], claim: dict[str, Any], scenario: dict[str, Any]
) -> dict[str, Any]:
    """Keep live-discovered enum values honest without calling them an implementation PASS."""
    predicate = claim.get("predicate", {})
    if row.get("status") not in {"PASS", "FAIL"} or predicate.get("operator") != "one_of":
        return row
    path = str(claim.get("target", {}).get("path") or "")
    values = scenario.get("values", {})
    if not isinstance(values, dict):
        return row
    contextual = values.get(path, MISSING)
    if contextual is MISSING and path:
        contextual = values.get(path.rsplit(".", 1)[-1], MISSING)
    if contextual is MISSING or not strict_equal(contextual, row.get("observed")):
        return row
    if any(strict_equal(contextual, allowed) for allowed in predicate.get("allowed_values", [])):
        return row
    return {
        **row,
        "status": "REVIEW",
        "reason_code": "plan.live_value_gap",
        "reason": (
            "The live-selected value is measured coherently but is absent from the "
            "tracking plan's allowed-value list."
        ),
        "check_next": "Confirm the live value and update or constrain the tracking plan.",
    }


def _domain_rollup(inspections: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    output = {}
    for domain in DOMAINS:
        rows = [row for row in inspections if row.get("domain") == domain]
        if not rows:
            output[domain] = {
                "status": "NOT_APPLICABLE",
                "reason": "No applicable proof obligation in this scenario.",
                "checks": 0,
            }
            continue
        status = worst_status((row["status"] for row in rows), default="NOT_APPLICABLE")
        reason = next((row["reason"] for row in rows if row["status"] == status), rows[0]["reason"])
        output[domain] = {"status": status, "reason": reason, "checks": len(rows)}
    return output


def _scenario_status(domains: dict[str, dict[str, Any]]) -> str:
    return worst_status((row["status"] for row in domains.values()), default="PENDING")


def _pre_action_result(
    event: dict[str, Any], coverage: dict[str, Any], *, compile_blocked: bool
) -> dict[str, Any]:
    status = "BLOCKED" if compile_blocked else "PENDING"
    reason = (
        "The event's plan slice is not executable: " + " | ".join(event["compile_errors"])
        if compile_blocked
        else "No committed action/scenario has been inspected yet."
    )
    domain_status = {
        domain: {
            "status": ("BLOCKED" if compile_blocked and domain == "source" else "NOT_APPLICABLE")
            if compile_blocked
            else "PENDING",
            "reason": "Plan compilation blocked this event."
            if compile_blocked
            else "Awaiting first action.",
            "checks": 0,
        }
        for domain in DOMAINS
    }
    return {
        "event_id": event["event_id"],
        "event_name": event.get("event_name"),
        "label": event.get("label"),
        "status": status,
        "final": False,
        "reason": reason,
        "domains": domain_status,
        "gates": {
            "evidence_confidence": {
                "status": status,
                "reason": "Affected claims were not compiled."
                if compile_blocked
                else "No action evidence yet.",
            },
            "scenario_completeness": coverage,
        },
        "coverage": coverage,
        "scenarios": [],
        "inspections": [],
        "claim_count": event.get("claim_count", 0),
    }


def _claim_inspection(
    claim: dict[str, Any],
    group: dict[str, Any],
    evidence: dict[str, list[dict[str, Any]]],
    model: dict[str, Any],
    event: dict[str, Any],
) -> dict[str, Any]:
    scenario_id = group["scenario_id"]
    applicability = _applicable(claim, group)
    if applicability is False:
        return _inspection(
            claim,
            "NOT_APPLICABLE",
            "claim.not_applicable",
            "The scenario applicability predicate is proven false.",
            expected=claim.get("applicability"),
            scenario_id=scenario_id,
        )
    if applicability is None:
        return _inspection(
            claim,
            "BLOCKED",
            "claim.applicability_unknown",
            "The claim applicability predicate cannot be resolved from scenario evidence.",
            expected=claim.get("applicability"),
            check_next="Scenario applicability value",
            scenario_id=scenario_id,
        )
    effective_claim = claim
    predicate = claim.get("predicate", {})
    path = str(claim.get("target", {}).get("path") or "")
    values = group.get("values", {})
    contextual = MISSING
    if isinstance(values, dict) and path:
        contextual = path_value(values, path)
        if contextual is MISSING:
            contextual = values.get(path.rsplit(".", 1)[-1].replace("[]", ""), MISSING)
    if (
        contextual is not MISSING
        and predicate.get("operator") in {"present", "one_of"}
        and claim.get("archetype") in {"source", "gtm", "delivery"}
    ):
        effective_claim = {
            **claim,
            "predicate": {
                "operator": "equals",
                "expected": contextual,
                **(
                    {"expected_type": predicate["expected_type"]}
                    if predicate.get("expected_type")
                    else {}
                ),
                **(
                    {"wire_coercion": True}
                    if claim.get("target", {}).get("surface") == "network"
                    else {}
                ),
            },
        }
    row = _evaluate_claim(effective_claim, evidence, model, event, scenario_id)
    return _apply_live_plan_gap(row, claim, group)


def _execution_protocol_inspection(
    event: dict[str, Any], action: dict[str, Any], scenario_id: str
) -> dict[str, Any]:
    claim = {
        "claim_id": f"{event['event_id']}::EXECUTION",
        "domain": "behavior",
        "target": {"check": "execution_protocol", "label": "Browser action protocol"},
        "predicate": {"operator": "present"},
        "label": "Browser action protocol",
    }
    violations = [row for row in action.get("execution_violations", []) if isinstance(row, dict)]
    if violations:
        return _inspection(
            claim,
            "BLOCKED",
            "execution.protocol_violation",
            "Browser control departed from the frozen action card; captured client evidence is preserved but confidence is blocked.",
            observed=[
                {
                    "code": row.get("code"),
                    "reason": row.get("reason"),
                    "observed": row.get("observed"),
                }
                for row in violations
            ],
            expected=action.get("action_card"),
            evidence=[action.get("commit_record_id")],
            check_next="Retest only the affected action with the same action card and no extra load",
            scenario_id=scenario_id,
        )
    return _inspection(
        claim,
        "PASS",
        "execution.protocol_observed",
        "The browser action stayed within its target navigation/reload/reset budget.",
        observed=action.get("operation_deltas", {}),
        expected=action.get("action_card"),
        evidence=[action.get("commit_record_id")],
        scenario_id=scenario_id,
    )


def _inspect_action(
    event: dict[str, Any],
    plan: dict[str, Any],
    model: dict[str, Any],
    group: dict[str, Any],
    action: dict[str, Any],
) -> list[dict[str, Any]]:
    scenario_id = group["scenario_id"]
    action_id = action["action_id"]
    evidence = _evidence_with_neighbors(model, action)
    rows = [
        _binding_result(event, plan, model, scenario_id, evidence=evidence, action=action),
        _settlement_inspection(event, evidence, scenario_id),
        _execution_protocol_inspection(event, action, scenario_id),
    ]
    acquisition = _acquisition_inspection(event, action, evidence, scenario_id)
    if acquisition is not None:
        rows.append(acquisition)
    rows.extend(
        _claim_inspection(claim, group, evidence, model, event) for claim in event.get("claims", [])
    )
    rows.extend(_consent_inspections(event, evidence, scenario_id))
    for row in rows:
        row["action_id"] = action_id
    return rows


def _inspect_scenario(
    event: dict[str, Any],
    plan: dict[str, Any],
    model: dict[str, Any],
    records: list[dict[str, Any]],
    group: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    scenario_id = group["scenario_id"]
    inspections: list[dict[str, Any]] = []
    if not group["actions"]:
        inspections.append(
            {
                "claim_id": f"{event['event_id']}::ACTION",
                "scenario_id": scenario_id,
                "domain": "reality",
                "inspection_target": "Scenario action",
                "status": "PENDING",
                "reason_code": "action.pending",
                "reason": "The scenario has no committed action.",
                "observed": None,
                "expected": "Committed safe action",
                "check_next": "Execute the scenario action",
                "evidence": [],
                "target": {"check": "action"},
            }
        )
    for action in group["actions"]:
        inspections.extend(_inspect_action(event, plan, model, group, action))
    inspections.extend(_semantic_annotations(records, event["event_id"], scenario_id))
    domains = _domain_rollup(inspections)
    return (
        {
            "scenario_id": scenario_id,
            "label": group["label"],
            "values": group["values"],
            "behavior_signature": group.get("behavior_signature"),
            "status": _scenario_status(domains),
            "domains": domains,
            "action_ids": [action["action_id"] for action in group["actions"]],
        },
        inspections,
    )


def _event_rollup(
    inspections: list[dict[str, Any]], coverage: dict[str, Any]
) -> tuple[str, dict[str, Any], dict[str, dict[str, Any]]]:
    domains = _domain_rollup(inspections)
    functional = worst_status((row["status"] for row in inspections), default="PENDING")
    if functional == "FAIL":
        status = "FAIL"
    elif coverage.get("status") == "PENDING":
        status = "PENDING"
    elif functional == "BLOCKED" or coverage.get("status") == "BLOCKED":
        status = "BLOCKED"
    elif functional == "REVIEW":
        status = "REVIEW"
    else:
        status = "PASS"
    blockers = [row for row in inspections if row["status"] == "BLOCKED"]
    confidence = {
        "status": "BLOCKED" if blockers else "PASS",
        "reason": blockers[0]["reason"]
        if blockers
        else "Every applicable claim has sufficient attributable evidence.",
        "blocked_claims": [row["claim_id"] for row in blockers],
    }
    return status, confidence, domains


def judge_event(
    run_dir: Any,
    plan: dict[str, Any],
    records: list[dict[str, Any]],
    event_id: str,
    *,
    model: dict[str, Any] | None = None,
) -> dict[str, Any]:
    event = event_by_id(plan, event_id)
    coverage = coverage_result(plan, records, event_id)
    model = model if model is not None else build_model(run_dir, plan, records)
    model["plan_events"] = plan.get("events", [])
    groups = _scenario_groups(model, event, coverage)
    if event.get("compile_errors"):
        return _pre_action_result(event, coverage, compile_blocked=True)
    if not groups:
        return _pre_action_result(event, coverage, compile_blocked=False)

    scenario_results: list[dict[str, Any]] = []
    all_inspections: list[dict[str, Any]] = []
    for group in groups:
        scenario, inspections = _inspect_scenario(event, plan, model, records, group)
        scenario_results.append(scenario)
        all_inspections.extend(inspections)

    status, confidence, domains = _event_rollup(all_inspections, coverage)
    reason_row = next(
        (row for row in all_inspections if row["status"] == status),
        next(
            (row for row in all_inspections if row["status"] in {"FAIL", "BLOCKED", "REVIEW"}),
            None,
        ),
    )
    return {
        "event_id": event_id,
        "event_name": event.get("event_name"),
        "label": event.get("label"),
        "status": status,
        "final": coverage.get("complete") is True and status != "PENDING",
        "reason": reason_row["reason"]
        if reason_row
        else "All applicable proof obligations passed.",
        "domains": domains,
        "gates": {
            "evidence_confidence": confidence,
            "scenario_completeness": coverage,
        },
        "coverage": coverage,
        "scenarios": scenario_results,
        "inspections": all_inspections,
        "claim_count": event.get("claim_count", 0),
    }


def _run_finished(records: list[dict[str, Any]]) -> bool:
    finished = False
    for record in records:
        if record.get("kind") == "RUN_FINISHED":
            finished = True
        elif record.get("kind") == "RUN_REOPENED":
            finished = False
    return finished


def judge_run(run_dir: Any, plan: dict[str, Any], records: list[dict[str, Any]]) -> dict[str, Any]:
    model = build_model(run_dir, plan, records)
    model["plan_events"] = plan.get("events", [])
    events = [
        judge_event(run_dir, plan, records, event["event_id"], model=model)
        for event in plan.get("events", [])
    ]
    status = worst_status((event["status"] for event in events), default="PENDING")
    return {
        "schema_version": plan.get("schema_version"),
        "run_id": plan.get("run_id"),
        "status": status,
        "finished": _run_finished(records),
        "events": events,
        "counts": {
            status_name: sum(event["status"] == status_name for event in events)
            for status_name in ("PASS", "FAIL", "BLOCKED", "REVIEW", "PENDING", "NOT_APPLICABLE")
        },
    }
