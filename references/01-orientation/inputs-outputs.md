# Inputs And Outputs

## Essential inputs

- Existing tracking plan or explicit analyst-defined acceptance rule.
- Target website/environment.

Accept the original XLSX, CSV, exported sheet, document, screenshot, mock-up, or
analyst explanation. Never require the analyst to rewrite it into a template.

## Supporting inputs

Collect when known or applicable:

- GTM account, web container, workspace, and Preview environment;
- supplied journeys, URLs, selectors, visible labels, screenshots, or mock-ups;
- consent scenarios required by the specification;
- approved test identities or synthetic-data constraints;
- browser/device context and execution date.

Missing journey instructions are not a blocker when relevant interactions can
be inferred safely. Missing consent scenarios are not a blocker when consent is
outside scope and the normal functional choice can be used.

Preserve source file, sheet, row, cell, section, screenshot, and original plan
order when normalizing.

## Continuous output

After each tested event, return a concise `PASS`, `FAIL`, `BLOCKED`, `REVIEW`,
or `NOT_TESTED` verdict. For a non-pass, state the precise evidence-backed
reason. Continue automatically unless analyst action is required.

## Final outputs

Return:

- one complete event-status list in original plan order;
- a schema-v2 normalized evidence file;
- a validated `.xlsx` with client summary, requirement matrix, journey
  coverage, event, tag, consent, unexpected-item, blocker, evidence, and run
  context sheets.

The recette is achieved by complete operational coverage and trustworthy
comparison. The workbook is its durable delivery artifact.
