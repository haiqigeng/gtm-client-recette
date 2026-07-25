# Completion Gates

Strict semantic validation rejects:

- missing plan or analyst-defined acceptance source;
- schema version other than 2;
- missing, duplicate, or out-of-order requirement/event inventories;
- source-bound requirements without source references;
- full runs with uncovered requirements;
- placeholder or prose raw payloads;
- occurred events without exact Tag Assistant API Call evidence;
- raw and resolved evidence collapsed together;
- `PASS` without actual value, state, type, and evidence;
- fixed mismatches hidden behind `PASS`;
- undocumented transformations;
- concerned tags without configuration/firing evidence;
- runtime parameter `PASS` without runtime value and type;
- wanted non-fired tags without reason and source;
- unrelated tags used as primary comparisons;
- event absence without a valid settled action boundary;
- `NOT_TESTED` used for an attempted blocker;
- final protected `BLOCKED` when analyst help was never requested;
- natural CMP and override evidence merged together;
- session override without explicit approval, test-CMP blocker, or
  non-production environment;
- unknown or duplicate evidence IDs;
- overall verdicts that hide worse component statuses.

The agent additionally verifies the authenticity of browser evidence, coverage
of relevant alternate journeys, final ordered event feedback, and workbook
readability. A structural validator cannot prove that browser observations are
truthful.

If a gate fails, report the run as incomplete and name the exact missing or
blocked evidence.
