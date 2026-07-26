# Completion Gates

Strict semantic validation rejects:

- missing plan or analyst-defined acceptance source;
- schema version other than 2;
- missing, duplicate, or out-of-order requirement/event inventories;
- source-bound requirements without source references;
- full runs with uncovered requirements;
- an event declared covered after only a representative interaction while an
  applicable finite placement, branch, or material value remains unattempted;
- small finite value domains that affect occurrence or payload but were sampled
  instead of exhausted, or large domains without a documented proportional
  coverage strategy;
- a controlled page-load, navigation, or interaction window with an
  unclassified explicit business push;
- duplicate, premature, delayed, wrong-order, or wrong-context planned events
  omitted from the verdict because their payload was valid;
- placeholder or prose raw payloads;
- planned dataLayer events without exact Tag Assistant API Call evidence;
- required raw/resolved/variable/tag-configuration layers without their own
  component verdicts;
- non-dataLayer events without exact source evidence;
- raw and resolved evidence collapsed together;
- `PASS` without actual value, state, type, and evidence;
- fixed mismatches hidden behind `PASS`;
- undocumented transformations;
- concerned tags without configuration/firing evidence;
- runtime parameter `PASS` without runtime value and type;
- destination `PASS` without browser-network evidence, with an omitted
  component verdict, or with a decoded vendor, destination ID, event name,
  endpoint, count, parameter, value, or type that does not match the raw
  browser request;
- trigger condition truth, blocking exceptions, or exact tag sequence that
  contradicts a `PASS`;
- wanted non-fired tags without reason and source;
- unrelated tags used as primary comparisons;
- event absence without a valid settled action boundary;
- reviewed attempts without a boundary, unsafe/missing action-value metadata,
  invalid timestamps, or impossible event-cursor chronology;
- `NOT_TESTED` used for an attempted blocker;
- an encountered ordinary gate skipped without analyst exclusion or evidenced
  consequence, including an unsubmitted ordinary conversion on a confirmed
  non-production environment;
- final protected `BLOCKED` when analyst help was never requested;
- natural CMP and override evidence merged together;
- session override without explicit approval, test-CMP blocker, or
  non-production environment;
- advanced consent false PASSes, missing consent verdicts, or tag-level checks
  whose status contradicts expected/actual state;
- declared business rules that contradict deterministic evaluation or omit
  their component verdict;
- missing scan policy/verdict, incomplete scanned targets, invalid custom
  patterns, unredacted findings, or false-pass sensitive-data results;
- conditional branches without acquisition/attempt evidence;
- unknown containers or browser contexts and false-pass client checks;
- inconsistent or omitted previous-run regression evidence;
- evidence without source/kind/path/time/description provenance, sensitive
  catalogue prose, a kind/source mismatch, a nested reference bound to the
  wrong kind, or unknown/duplicate evidence IDs;
- missing explicit client-side container inventory or any server container;
- unallowlisted sensitive content left in the normalized record supplied to
  the workbook builder;
- overall verdicts that hide worse component statuses.

The agent additionally verifies the authenticity of browser evidence, complete
applicable interaction coverage, continuous business-stream reconciliation,
gate completion, relevant alternate journeys, final ordered event feedback,
and workbook readability. A structural validator cannot prove that browser
observations are truthful.

If a gate fails, report the run as incomplete and name the exact missing or
blocked evidence.
