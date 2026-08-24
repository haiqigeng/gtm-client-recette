# Verdict and output

## Tracking-plan authority

The compiler preserves source coordinates and creates typed occurrence, value/state,
relationship, order, transport, and negative proof obligations. It does not invent an
event, tag, destination, or browser send for a source-only/state-only requirement.

For an ordinary browser-delivered planned field, judge the same plan requirement at:

1. exact API Call source value;
2. concerned tag's effective mapping;
3. concerned tag's runtime value;
4. decoded browser request value.

Compare fields, not raw object size. A generic settings/ecommerce object may cover many
fields only when configuration or runtime proves that effective mapping. Complete tag
detail with one represented field out of twelve produces eleven mapping/runtime failures.

Contextual values are strict inside their scenario. `en` and `fr` may each pass on their
selected route; a product name may vary by selected product. But API Call, tag runtime,
and request for one action must agree even when the plan predicate is merely `present` or
contains several allowed values. Wire string coercion is allowed only for an explicitly
transport-compatible comparison.

Missing, undefined, null, empty, and populated remain distinct. Booleans are not numbers.

## Five user-facing layers

Every event feedback block always contains:

| Layer | What it proves |
|---|---|
| Page/action reality | Reachability, route/state, interaction/outcome, visible business truth |
| Data Layer API Call | Exact occurrence and planned source fields/values/types |
| GTM Tags | Inventory, mapping, firing count, runtime fields/values |
| Browser request | Logical send, destination, fields, outcome, duplicates/retries |
| Surrounding behavior | Chronology and human-like anomaly assessment |

An inapplicable browser request is explicitly `NOT_APPLICABLE`; it is not silently
omitted. Accumulated Data Layer, GTM Variables, consent, acquisition, recorder, form,
media, and protected diagnostics appear only when activated. Data safety, evidence
confidence, and scenario coverage appear when non-pass.

Internally, typed claim domains may remain useful for deterministic roll-up, but they are
not extra browser stages and must not expand the default feedback matrix.

## Evidence and causal rules

- Attribute evidence to browser context, tab, document/frame, action, Preview epoch/index,
  event, concerned tag, logical hit, and transport attempt when available.
- Consume only Preview indexes after the frozen cursor. A new epoch starts at zero with
  a matching rebound identity.
- The fully expanded API Call is normal source authority. Accumulated state and Variables
  are diagnostics, never substitutes.
- A tag may fire on a causal technical follow-up such as Trigger Group. Stop that causal
  window at the next unrelated business event.
- Keep every post-cursor business API Call. One uncaused `add_to_cart` between planned
  interactions is a material interjection; routine GTM lifecycle rows are noise unless
  they change tracking state or verdict.
- Merge transport retries/redirects for one logical hit but keep duplicate logical hits
  separate.
- A settled complete source window proves a missing event `FAIL`; an incomplete source
  window is `BLOCKED`.
- A complete tag detail proves an absent mapping/runtime field `FAIL`; partial detail is
  `BLOCKED`.
- A complete attributable request window proves a missing request/parameter `FAIL`;
  incomplete request/body capture is `BLOCKED`.
- A dead/soft-404 page, failed form, unconfirmed purchase, stale product, or populated
  cart represented as empty fails regardless of technically coherent downstream layers.
- Wrong/unattributable browser or Preview binding blocks dependent checks and is not
  relabelled as a client implementation failure.
- An accidentally unaccepted ordinary CMP is a setup block; ask the user to accept it.
  Consent suppression is certified only in an explicit consent scenario.
- Agent/control violations preserve useful client evidence, block confidence where
  necessary, and never trigger an automatic cleanup repeat.

## Status and roll-up

- `PASS`: current attributable evidence proves the claim.
- `FAIL`: settled complete evidence contradicts it.
- `BLOCKED`: execution or observability prevents a trustworthy decision.
- `REVIEW`: one precise verdict-changing ambiguity remains.
- `NOT_APPLICABLE`: the plan/scenario creates no obligation.
- `PENDING`: required action or scenario coverage remains unfinished.

Precedence is `FAIL` > `BLOCKED` > `REVIEW` > `PENDING` > `PASS` >
`NOT_APPLICABLE`. A definite failure is not softened because another check is blocked.

## Immediate per-event feedback contract

`complete` is tolerant of partial capture. It commits usable evidence, builds the causal
model once, persists `EVENT_FEEDBACK_ISSUED`, and emits feedback before another action.
Omitted page, Preview, or network evidence creates explained `BLOCKED` layers; it does
not make the command refuse feedback.

Each event block contains:

- event and overall status/finality;
- scenario status when several scenarios exist;
- all five default layer rows in fixed order;
- status and passed/total checks for each layer;
- GTM subcounts for inventory, mapping, firing, and runtime;
- for every non-pass layer: exact reason, affected fields/checks, observed/expected when
  available, targeted `Check next`, and evidence IDs;
- conditional diagnostics/gates only when applicable or non-pass.

Every detailed claim remains in canonical JSON/XLSX with scenario, action, target,
status, observed, expected, reason code/reason, next check, and evidence. Grouping passing
rows must never hide differing or non-pass fields.

Late continuous evidence may revise the immediately preceding event. Emit that revised
event feedback in the same completion response; never silently mutate it.

## Finalization

`finish` refuses open actions/protected handoffs and non-final coverage, then renders:

- plan-ordered `conclusion.md` whose event table contains all five layer statuses and why;
- canonical `results.json`;
- validated `results.xlsx` with five-layer event summary, scenarios, detailed
  inspections, defects/limits, evidence index, and telemetry;
- concise sidecars where generated.

Outputs are formula-safe and privacy-safe. Only action-scoped concerned evidence can
affect an event's safety verdict. `report` rebuilds from the frozen run; `reopen` requires
explicit authorization. The deterministic renderer owns statuses. Analyst reasoning may
only add an evidence-backed `FAIL` or `REVIEW`.
