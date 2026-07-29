# Completion Gates

Strict semantic validation rejects:

- missing plan or analyst-defined acceptance source;
- schema version other than 2;
- missing, duplicate, or out-of-order requirement/event inventories;
- source-bound requirements without source references;
- full runs with uncovered requirements;
- a pending case, open action, missing retry lineage, or a normalized action
  boundary that differs from the retained session action;
- an event declared covered after only a representative interaction while an
  applicable finite placement, branch, or material value remains unattempted;
- small finite value domains that affect occurrence or payload but were sampled
  instead of exhausted, or large domains without a documented proportional
  coverage strategy;
- a controlled page-load, navigation, or interaction window with an
  unclassified explicit business push;
- an action's observed business-push count that differs from its classified
  stream rows, or an anomalous push missing from `unexpected`;
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
- a concerned tag without an explicit `browser_request` or `local_only`
  delivery declaration;
- a browser-sending tag without destination/event identity, endpoint, request
  count, decoded parameters, or a first-party request tied to the action and
  client container;
- runtime parameter `PASS` without runtime value and type;
- destination `PASS` without browser-network evidence, with an omitted
  component verdict, or with a decoded vendor, destination ID, event name,
  endpoint, count, parameter, value, or type that does not match the raw
  browser request;
- trigger condition truth, blocking exceptions, or exact tag sequence that
  contradicts a `PASS`;
- wanted non-fired tags without reason and source;
- unrelated tags used as primary comparisons;
- event absence without an independently completed interaction and valid
  settled relevant-stream boundary;
- reviewed attempts without a boundary, unsafe/missing action-value metadata,
  invalid timestamps, or impossible event-cursor chronology;
- `REVIEW` without `review_basis: semantic_ambiguity` and the exact question
  requiring analyst judgement;
- final `PENDING`, or `REVIEW` used to hide missing execution/evidence;
- `NOT_TESTED` used for an attempted blocker;
- an encountered ordinary gate skipped without analyst exclusion or evidenced
  consequence, including an unsubmitted ordinary conversion on a confirmed
  non-production environment;
- final protected `BLOCKED` when analyst help was never requested;
- natural CMP and override evidence merged together;
- session override without explicit approval, session-only scope, non-PASS
  native-CMP status, or the appropriate environment blocker;
- production CMP override without a distinct production exception,
  production approval evidence, exact method, and restoration confirmation;
- advanced consent false PASSes, missing consent verdicts, or tag-level checks
  whose status contradicts expected/actual state;
- declared business rules that contradict deterministic evaluation or omit
  their component verdict;
- missing scan policy/verdict, incomplete scanned targets, invalid custom
  patterns, unredacted findings, or false-pass sensitive-data results;
- conditional branches without acquisition/attempt evidence;
- unknown containers or browser contexts and false-pass client checks;
- inconsistent or omitted previous-run regression evidence;
- evidence without source/kind/capture-mode/path/time/description provenance,
  direct action/event/container/request linkage when applicable, sensitive
  catalogue prose, a kind/source mismatch, reconstructed evidence presented as
  direct proof, a nested reference bound to the wrong kind, or
  unknown/duplicate evidence IDs;
- credentials or synthetic personal fields retained in the session ledger;
- missing explicit client-side container inventory or any server container;
- unallowlisted sensitive content left in the normalized record supplied to
  the workbook builder;
- overall verdicts that hide worse component statuses.

Final validation cross-checks the normalized result with the case/action
session ledger, direct evidence linkage, layer completion, and classified push
counts. The agent additionally verifies the authenticity of browser evidence,
that the case census itself is complete, independent non-tracking proof that
each judged action completed, controlled reconciliation of any journal/Preview
gap, safe gate completion, relevant alternate journeys, immediate event
feedback, and workbook readability. No structural validator can independently
prove that browser observations are truthful.

If a gate fails, report the run as incomplete and name the exact missing or
blocked evidence.
