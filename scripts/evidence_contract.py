#!/usr/bin/env python3
"""Shared direct-evidence provenance and linkage rules."""

from __future__ import annotations

DIRECT_CAPTURE_KINDS = {
    "action_boundary",
    "api_call",
    "resolved_data_layer",
    "gtm_variable",
    "tag_configuration",
    "tag_runtime",
    "browser_interception",
    "browser_network_request",
    "browser_console",
    "console_error",
    "vendor_helper",
    "trigger_evaluation",
    "tag_sequence",
    "tag_assistant_consent",
    "consent_state",
    "client_side_checks",
    "screenshot",
    "navigation",
    "source_signal",
    "gtm_native_event",
    "gtm_auto_event",
    "dom_event",
    "direct_vendor_call",
    "custom_html",
    "ga4_enhanced_measurement",
}

DETERMINISTIC_CAPTURE_KINDS = {
    "business_rule_evaluation",
    "sensitive_data_scan",
    "previous_run_comparison",
}

ANALYST_CAPTURE_KINDS = {
    "analyst_approval",
    "scenario_branch",
}

CAPTURE_MODES = {"direct", "deterministic", "analyst_supplied", "supplemental"}

ACTION_BOUND_EVIDENCE_KINDS = DIRECT_CAPTURE_KINDS - {
    "tag_configuration",
    "screenshot",
    "navigation",
}

EVENT_INDEX_EVIDENCE_KINDS = {
    "api_call",
    "browser_interception",
    "resolved_data_layer",
    "gtm_variable",
    "tag_runtime",
    "trigger_evaluation",
    "tag_sequence",
    "tag_assistant_consent",
    "consent_state",
    "direct_vendor_call",
    "gtm_native_event",
    "gtm_auto_event",
}

CONTAINER_BOUND_EVIDENCE_KINDS = {
    "api_call",
    "resolved_data_layer",
    "gtm_variable",
    "tag_configuration",
    "tag_runtime",
    "browser_network_request",
    "trigger_evaluation",
    "tag_sequence",
    "tag_assistant_consent",
}
