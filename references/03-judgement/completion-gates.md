# Completion Gates

Strict validation must reject:

- missing run context for site URL, container ID, workspace, or plan source;
- no detailed checks or evidence catalogue;
- missing or invalid statuses;
- result rows without evidence IDs;
- evidence IDs not present in the evidence catalogue;
- duplicate evidence IDs;
- wanted-but-not-fired tags or tag checks without a reason and reason source.
- no canonical comparison rows;
- comparison rows missing tracking-plan, dataLayer, or tag-configuration values.

The agent must additionally verify that all planned events, variables, tags,
parameters, consent scenarios, and relevant unexpected items have been covered.
Every business action must have a readiness checkpoint, action boundary, and
settled event-stream checkpoint. Every canonical comparison must preserve the
tracking-plan source and each observed value without collapsing mismatches.
The workbook builder validates report structure; it cannot verify that a browser
observation is truthful.

If a gate fails, deliver `Incomplete / blocked` with the exact missing item.
