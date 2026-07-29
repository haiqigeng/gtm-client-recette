# Inputs And Outputs

## Essential inputs

- Existing tracking plan or explicit analyst-defined acceptance rule.
- Target website/environment.

Accept the original XLSX, CSV, exported sheet, document, screenshot, mock-up, or
analyst explanation. Never require the analyst to rewrite it into a template.
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
  comparison evidence.

Missing journey instructions are not a blocker when relevant interactions can
be inferred safely. Missing consent scenarios are not a blocker when consent is
outside scope and the normal functional choice can be used.

Preserve source file, sheet, row, cell, section, screenshot, and original plan
order when normalizing.

## Continuous output

After all applicable cases for each tested event, return one concise `PASS`,
`FAIL`, `BLOCKED`, `REVIEW`, or `NOT_TESTED` verdict. Group homogeneous
successes by tested count and identify each distinct non-pass case with its
precise evidence-backed reason, verified layer statuses, and exact website
retest interaction. Continue automatically unless analyst action is required.

## Final outputs

Return:

- one complete event-status list in original plan order;
- a schema-v2 normalized evidence file retaining action outcome, independent
  completion signal, linked retry attempts, and adaptive settlement evidence;
- a session ledger retaining every interaction case, attempt, applicable layer
  result, safe run authorization, and classified chronological business push;
- a validated `.xlsx` with client summary, requirement matrix, journey
  coverage, interaction-case, event, observed-push-stream, tag, destination,
  trigger/sequence, consent, business-rule, sensitive-data, client-check,
  regression, container, unexpected-item, blocker, evidence, and run-context
  sheets.

The recette is achieved by complete operational coverage and trustworthy
comparison. The workbook is its durable delivery artifact.
