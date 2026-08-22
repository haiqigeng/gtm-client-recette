# Evidence and layer contract

## Mandatory defaults

The 19 canonical rows are always present, but they are not all substantive by
default. For a normal planned dataLayer event with a browser-sending tag, the
default mandatory chain is:

1. action boundary;
2. exact raw API Call/dataLayer payload;
3. resolved Data Layer event state;
4. complete concerned-tag inventory;
5. GTM variables consumed or positively unused;
6. tag configuration;
7. firing/non-firing and count;
8. runtime tag parameters and JSON types;
9. matching browser destination request;
10. sensitive-data scan.

Destination is not applicable only for a positively proved local-only tag. A
non-dataLayer source replaces raw/resolved proof with direct source-signal proof
but retains every applicable downstream tag layer. Consent, trigger, sequence,
business rules, client checks, regression, multi-container context, and scenario
branches activate when their recorded predicates are true.

## Canonical matrix

Record all rows in canonical order: `action_boundary`, `raw_api_call`,
`resolved_data_layer`, `concerned_tag_inventory`, `gtm_variable`,
`tag_configuration`, `tag_firing`, `tag_parameter`,
`destination_request_when_applicable`, `sensitive_data_scan`,
`consent_when_applicable`, `source_signal_when_no_data_layer_push`,
`trigger_logic_when_applicable`, `tag_sequence_when_applicable`,
`business_rules_when_declared`, `client_checks_when_applicable`,
`regression_when_baseline_provided`, `container_context_when_applicable`, and
`conditional_scenarios_when_applicable`.

A false conditional row is explicit `NOT_APPLICABLE` with predicate, reason,
and proof. Never omit a row.

For each in-scope tag, record eight tag-bound rows: variable, configuration,
firing, runtime parameter, destination, consent, trigger, and sequence. Each row
uses that exact frozen tag identity and evidence.

## Non-substitutive chain

Raw and resolved values are different evidence. Firing does not prove correct
configuration or parameters. Runtime values do not prove their configured
source. A network request proves an attempted browser send, not vendor receipt,
attribution, or reporting.

Expected anchors come from the plan, visible page/business state, a direct
interaction, or documented platform semantics. Compare absence, undefined,
null, empty, value, JSON type, occurrence count, action window, context, and
order exactly. Every evidence artifact used by a final verdict must be a local
file whose complete catalog binding and content digest are verified before
final output; an external URL alone is not immutable proof.
