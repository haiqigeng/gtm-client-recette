from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tests.v5_harness import V5Harness, default_event

from core.state import StateError
from core.workflow import commit_action, sync_preview

TAXONOMY_DIMENSIONS = {f"X{index}" for index in range(1, 14)}
MUTATIONS = {
    "delete",
    "duplicate",
    "insert",
    "reorder",
    "delay",
    "split",
    "merge",
    "substitute",
    "carry_over",
    "obscure",
    "interrupt",
    "scale",
}
FAILED_RUN_CASES = {f"FR{index:02d}" for index in range(1, 33)}

# Every catalogue item resolves to a small general contract; the catalogue is not
# copied into runtime branches. Representative executable tests below falsify each
# contract, while browser-UI-only items remain instruction/real-pilot gates.
STRESS_CROSSWALK = {
    **{key: "occurrence_identity_and_confidence" for key in ("X1", "X2", "X5", "X10")},
    **{key: "business_state_and_value_semantics" for key in ("X3", "X4", "X7")},
    "X6": "continuous_causality",
    "X8": "material_scenario_coverage",
    "X9": "typed_consent_acquisition",
    "X11": "safety_and_integrity",
    "X12": "bounded_reuse_and_scale",
    "X13": "renderer_owned_verdicts",
    **{key: "mutation_algebra" for key in MUTATIONS},
    **{
        key: contract
        for keys, contract in (
            (("FR01", "FR03", "FR05", "FR17", "FR22"), "occurrence_identity_and_confidence"),
            (("FR02", "FR26", "FR29"), "bounded_action_lifecycle"),
            (
                ("FR04", "FR08", "FR09", "FR14", "FR15", "FR23", "FR24", "FR28"),
                "claim_specific_authority",
            ),
            (("FR10", "FR11", "FR12", "FR18", "FR19", "FR20", "FR21"), "lossless_typed_compiler"),
            (("FR06", "FR07", "FR16", "FR30"), "operator_instruction_and_bounded_recovery"),
            (("FR13",), "runtime_tag_discovery_review"),
            (("FR25",), "immutable_plan_new_run_boundary"),
            (("FR27",), "tool_failure_attribution"),
            (("FR31",), "claims_share_occurrences"),
            (("FR32",), "no_run_specific_runtime_state"),
        )
        for key in keys
    },
}


class StressContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_every_taxonomy_dimension_mutation_and_failed_run_case_is_mapped(self) -> None:
        expected = TAXONOMY_DIMENSIONS | MUTATIONS | FAILED_RUN_CASES
        self.assertEqual(set(STRESS_CROSSWALK), expected)
        self.assertNotIn("UNMAPPED", set(STRESS_CROSSWALK.values()))

    def test_source_mutation_algebra_never_creates_false_pass(self) -> None:
        cases = {
            "baseline": ([{"event": "view_item"}], "PASS"),
            "delete": ([], "FAIL"),
            "duplicate": ([{"event": "view_item"}, {"event": "view_item"}], "FAIL"),
            "substitute": ([{"event": "purchase"}], "FAIL"),
        }
        for name, (payloads, expected) in cases.items():
            with self.subTest(name=name):
                harness = V5Harness(self.root / name)
                action = harness.begin()
                harness.commit(action, payloads)
                preview_payloads = [{"event": "view_item"}] if name != "delete" else []
                result = harness.sync(
                    ["E-view_item"],
                    preview_payloads,
                    action_id=action,
                    coverage=harness.coverage("E-view_item", [action]),
                )["events"][0]
                self.assertEqual(result["status"], expected)

    def test_obscured_source_is_blocked_instead_of_failed_or_passed(self) -> None:
        harness = V5Harness(self.root)
        action = harness.begin()
        payload = {
            "event": "view_item",
            "ecommerce": {
                "__gtm_recette_type": "snapshot_truncated",
                "reason": "max_nodes",
            },
        }
        harness.commit(action, [payload])
        result = harness.sync(
            ["E-view_item"],
            [payload],
            action_id=action,
            coverage=harness.coverage("E-view_item", [action]),
        )["events"][0]
        self.assertEqual(result["domains"]["source"]["status"], "BLOCKED")
        self.assertNotEqual(result["status"], "PASS")

    def test_document_and_preview_epoch_identity_mismatches_block_attribution(self) -> None:
        harness = V5Harness(self.root)
        action = harness.begin()
        payload = {"event": "view_item"}
        datalayer = harness.datalayer([payload], action_id=action)
        datalayer["records"][0]["documentId"] = "DOC-OLD"
        bundle = {
            "health": harness._health("after"),
            "page": {"states": [harness._page("after")]},
            "datalayer": datalayer,
            "network": harness.network(["view_item"], action_id=action),
        }
        commit_action(harness.run, bundle, action_id=action)
        result = harness.sync(
            ["E-view_item"],
            [payload],
            action_id=action,
            coverage=harness.coverage("E-view_item", [action]),
        )["events"][0]
        identity = next(
            row
            for row in result["inspections"]
            if row["reason_code"] == "binding.occurrence_identity_mismatch"
        )
        self.assertEqual(identity["status"], "BLOCKED")

    def test_static_configuration_reuse_requires_exact_container_workspace_identity(self) -> None:
        events = [default_event("E-list", "view_item_list"), default_event("E-item", "view_item")]

        def second_result(root: Path, workspace_version: str) -> dict:
            harness = V5Harness(root, events=events)
            first = harness.begin(["E-list"])
            first_payload = {"event": "view_item_list"}
            harness.commit(first, [first_payload])
            harness.sync(
                ["E-list"],
                [first_payload],
                action_id=first,
                coverage=harness.coverage("E-list", [first]),
            )

            second = harness.begin(["E-item"])
            second_payload = {"event": "view_item"}
            harness.commit(second, [second_payload])
            preview = harness.preview([second_payload], action_id=second)
            preview["workspace_version"] = workspace_version
            preview["events"][0]["workspace_version"] = workspace_version
            preview["events"][0]["tags"][0]["configuration"] = None
            return sync_preview(
                harness.run,
                {
                    "preview": preview,
                    "coverage": harness.coverage("E-item", [second]),
                },
                event_ids=["E-item"],
            )["events"][0]

        reused = second_result(self.root / "same", "42")
        reused_configuration = next(
            row
            for row in reused["inspections"]
            if row["inspection_target"] == "Tag configuration - GA4 event"
        )
        self.assertEqual(reused_configuration["status"], "PASS")
        self.assertTrue(reused_configuration["observed"]["reused_static"])

        changed = second_result(self.root / "changed", "43")
        changed_configuration = next(
            row
            for row in changed["inspections"]
            if row["inspection_target"] == "Tag configuration - GA4 event"
        )
        self.assertEqual(changed_configuration["status"], "BLOCKED")

    def test_unsettled_action_cannot_receive_definitive_pass(self) -> None:
        harness = V5Harness(self.root)
        action = harness.begin()
        payload = {"event": "view_item"}
        health = harness._health("after")
        health["settled"] = False
        health["settlement_reason"] = "request still pending"
        commit_action(
            harness.run,
            {
                "health": health,
                "page": {"states": [harness._page("after")]},
                "datalayer": harness.datalayer([payload], action_id=action),
                "network": harness.network(["view_item"], action_id=action),
            },
            action_id=action,
        )
        result = harness.sync(
            ["E-view_item"],
            [payload],
            action_id=action,
            coverage=harness.coverage("E-view_item", [action]),
        )["events"][0]
        self.assertEqual(result["domains"]["behavior"]["status"], "BLOCKED")
        self.assertFalse(result["status"] == "PASS")

    def test_unnamed_in_scope_tag_is_discovered_but_not_silently_certified(self) -> None:
        event = default_event()
        event["tags"] = []
        harness = V5Harness(self.root, events=[event])
        action = harness.begin()
        payload = {"event": "view_item"}
        harness.commit(action, [payload])
        preview = harness.preview([payload], action_id=action)
        preview_event = preview["events"][0]
        preview_event["fired_tags"] = ["runtime-ga4"]
        preview_event["tags"] = [
            {
                "tag_id": "runtime-ga4",
                "tag_name": "GA4 product event",
                "category": "GA4",
                "fired": True,
                "configuration": {"measurement_id": "G-TEST123"},
            }
        ]
        result = sync_preview(
            harness.run,
            {
                "preview": preview,
                "coverage": harness.coverage("E-view_item", [action]),
            },
            event_ids=["E-view_item"],
        )["events"][0]
        discovery = next(
            row
            for row in result["inspections"]
            if row["inspection_target"] == "Runtime in-scope tag discovery"
        )
        self.assertEqual(discovery["status"], "REVIEW")
        self.assertEqual(result["status"], "REVIEW")

    def test_missing_request_parameter_with_partial_payload_is_blocked(self) -> None:
        event = default_event()
        event["requirements"].append(
            {
                "field_path": "currency",
                "match_rule": "equals",
                "expected_value": "EUR",
                "request_path": "currency",
                "tag_name": "GA4-event",
                "destination": "G-TEST123",
            }
        )
        harness = V5Harness(self.root, events=[event])
        action = harness.begin()
        payload = {"event": "view_item", "currency": "EUR"}
        network = harness.network(["view_item"], action_id=action)
        network["parameter_capture_complete"] = False
        commit_action(
            harness.run,
            {
                "health": harness._health("after"),
                "page": {"states": [harness._page("after")]},
                "datalayer": harness.datalayer([payload], action_id=action),
                "network": network,
            },
            action_id=action,
        )
        result = harness.sync(
            ["E-view_item"],
            [payload],
            action_id=action,
            coverage=harness.coverage("E-view_item", [action]),
        )["events"][0]
        request_parameter = next(
            row
            for row in result["inspections"]
            if row["inspection_target"] == "Request Parameter - currency"
        )
        self.assertEqual(request_parameter["status"], "BLOCKED")

    def test_first_consequential_action_requires_only_a_cheap_source_self_test(self) -> None:
        harness = V5Harness(self.root)
        with self.assertRaisesRegex(StateError, "source self-test"):
            harness.begin(replay_safety="CONSEQUENTIAL")
        safe = V5Harness(self.root / "proven")
        action = safe.begin(
            replay_safety="CONSEQUENTIAL",
            first_bundle_updates={
                "datalayer": safe.datalayer([{"event": "gtm.js"}], action_id=None)
            },
        )
        self.assertTrue(action.startswith("A-"))

    def test_state_only_message_is_not_forced_into_named_event_or_tag_semantics(self) -> None:
        event = {
            "event_id": "E-core-state",
            "label": "Core dataLayer state",
            "mode": "state_only",
            "requirements": [
                {
                    "field_path": "device_type",
                    "match_rule": "one_of",
                    "allowed_values": ["desktop", "mobile"],
                    "expected_type": "string",
                }
            ],
        }
        harness = V5Harness(self.root, events=[event])
        action = harness.begin(["E-core-state"])
        payload = {"device_type": "desktop", "site_country": "FR"}
        harness.commit(action, [payload], include_network=False)
        result = harness.sync(
            ["E-core-state"],
            [],
            action_id=action,
            coverage=harness.coverage("E-core-state", [action]),
            include_preview=False,
        )["events"][0]
        self.assertEqual(result["domains"]["source"]["status"], "PASS")
        self.assertEqual(result["domains"]["gtm"]["status"], "NOT_APPLICABLE")
        self.assertEqual(result["domains"]["delivery"]["status"], "NOT_APPLICABLE")
        self.assertEqual(result["status"], "PASS")

    def test_metamorphic_order_and_batch_changes_preserve_or_change_only_expected_claims(
        self,
    ) -> None:
        events = [default_event("E-list", "view_item_list"), default_event("E-item", "view_item")]
        ordered = V5Harness(self.root / "ordered", events=events)
        action = ordered.begin(["E-list", "E-item"])
        payloads = [{"event": "view_item_list"}, {"event": "view_item"}]
        ordered.commit(action, payloads)
        ordered_results = ordered.sync(
            ["E-list", "E-item"],
            payloads,
            action_id=action,
            coverage=[ordered.coverage("E-list", [action]), ordered.coverage("E-item", [action])],
        )["events"]
        self.assertTrue(all(row["status"] == "PASS" for row in ordered_results))

        reordered = V5Harness(self.root / "reordered", events=events)
        action = reordered.begin(["E-list", "E-item"])
        reverse = list(reversed(payloads))
        reordered.commit(action, reverse)
        reordered_results = reordered.sync(
            ["E-list", "E-item"],
            reverse,
            action_id=action,
            coverage=[
                reordered.coverage("E-list", [action]),
                reordered.coverage("E-item", [action]),
            ],
        )["events"]
        # No order oracle was declared, so reordering must not create an invented failure.
        self.assertTrue(all(row["status"] == "PASS" for row in reordered_results))


if __name__ == "__main__":
    unittest.main()
