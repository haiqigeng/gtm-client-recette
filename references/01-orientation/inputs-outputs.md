# Inputs And Outputs

## Essential inputs

- Existing tracking plan or explicit analyst-defined acceptance rule.
- Target website/environment.

Accept the original XLSX, CSV, exported sheet, document, screenshot, mock-up, or
analyst explanation. Never require the analyst to rewrite it into a template.
When a `ga4-tracking-plan` delivery directory is supplied, use
`scripts/import_ga4_tracking_plan_handoff.py` as the primary intake. It verifies the reviewed or
approved handoff and all hashes, then consumes `plan.json` plus `expected-events.json` directly;
the XLSX remains the human review surface and is not reparsed.
For XLSX input, preserve hyperlinks, cell comments, merged ranges, embedded
image anchors, source coordinates, and sheet order with
`scripts/inspect_tracking_plan.py`.

## Supporting inputs

Collect when known or applicable:

- GTM account, every applicable client-side web container, workspace, and
  Preview environment;
- supplied journeys, URLs, selectors, visible labels, screenshots, or mock-ups;
- known interaction placements, repeated controls, and finite input domains;
- consent scenarios required by the specification;
- approved test identities or synthetic-data constraints;
- browser/device context and execution date.
- available analyst-approved browser attachment or dedicated-session method;
- vendor/destination list, destination IDs, and media/analytics tag contracts;
- conditional branches, user states, or A/B acquisition method;
- accepted cross-field rules and sensitive-data allowlists;
- previous normalized recette and acceptance-relevant read-only container
  comparison evidence;
- optional Audit fact or Configuration change-manifest artifact, registered by
  digest as supporting-only context with no verdict authority.

Missing journey instructions are not a blocker when relevant interactions can
be inferred safely. Missing consent scenarios are not a blocker when consent is
outside scope and the normal functional choice can be used.

The plan is acceptance-value and journey support. It never selects the runtime
evidence layers. Missing plan tag columns do not authorize omission of tag,
runtime, or browser-request checks for a planned dataLayer event.

Declare tag scope separately from the plan:

- default `analytics_only`, while retaining an exact plan-declared media
  destination;
- explicit `all_relevant_client_side_tags`; or
- explicit fixed tag names.

A full recette also supplies default authority for ordinary form fields,
privacy acknowledgements, tested-conversion opt-ins, safe synthetic data, and
ordinary submission. CMP simulation remains a separate one-time approval.

Preserve source file, sheet, row, cell, section, screenshot, and original plan
order when normalizing.

## Continuous output

After all applicable cases for each tested event, return one concise aggregate
`PASS`, `FAIL`, `BLOCKED`, `REVIEW`, or `NOT_TESTED` verdict plus one explicit
status/reason for every canonical layer and every in-scope tag/layer pair.
Show conditional false rows as `NOT_APPLICABLE`, retain detected out-of-scope
tags visibly, and identify each non-pass row with direct evidence and the exact
website retest interaction. Continue automatically unless analyst action is
required.

## Final outputs

Return:

- one complete event-status list in original plan order;
- a schema-v3 normalized evidence file retaining action outcome, independent
  completion signal, linked retry attempts, and adaptive settlement evidence;
- a session ledger retaining every interaction case, attempt, immutable
  applicability card, detected-tag inventory and scope decision, per-layer and
  per-tag results, safe run authority, and classified chronological business
  push;
- a validated `.xlsx` with client summary, defect register, requirement matrix,
  journey coverage, interaction-case, event, layer-verdict, observed-push-stream,
  tag, destination,
  trigger/sequence, consent, business-rule, sensitive-data, client-check,
  regression, container, unexpected-item, blocker, evidence, and run-context
  sheets;
- optional concise defect CSV/Markdown and stakeholder Markdown sidecars,
  generated from the same validated result rather than maintained separately.

The recette is achieved by complete operational coverage and trustworthy
comparison. The workbook is its durable delivery artifact.
