# Verdict and output

## Proof obligations and evidence authority

The compiler preserves source coordinates and turns each accepted requirement into one
or more typed claims:

- occurrence: must fire, must not fire, or exact/count range;
- value/state: present, absent, undefined, null, empty, exact, enum, type, range or regex;
- relationship: values agree with each other or with current business reality;
- ordering: causal sequence or before/after constraints;
- transport: logical hit, destination, tag identity, browser request and outcome;
- negative: complete-window proof that an event/tag/request did not occur.

Tabular intake reports rows seen, compiled, inherited from a contiguous event identity,
and intentionally ignored. Merged/fill-down event cells are retained only inside one
contiguous table; a blank separator resets that context. Orphan or ambiguous requirement
rows stop intake before browser work. Malformed predicates become event-local compile
failures with source coordinates, so a later unsupported rule cannot block the first
valid event. Do not silently reinterpret a rule or invent missing tag scope. A
source-only/state-only claim remains source-oriented. For ordinary GA4 claims, the same
destination-applicable plan predicate is automatically checked at the exact API Call or
proven call-time source,
Tag Assistant accumulated Data Layer state, resolved Variables, effective tag mapping,
runtime payload, and decoded browser request without additional browser actions. The
comparison is per field, not a variable-count heuristic: object/settings or automatic
mappings count only when their effective runtime value is proved.

Machine evidence enters through typed capture adapters and receives stable identity.
Agent-authored notes may explain coverage or add an evidence-backed semantic `FAIL` or
`REVIEW`; they cannot create a machine observation or declare a pass. All public commands
feed the same compiler, occurrence model, confidence/coverage gates and deterministic
renderer.

## Six domains and two gates

The six domains are reporting/diagnostic groups, not a fixed checklist or serial
workflow. Operational rows remain distinct inside them.

1. `reality`: page/API status, soft 404, route/context, visible state, before/after change,
   independent action/form/purchase/business outcome.
2. `source`: exact-message occurrence, value/state/type and chronology, including
   state-only and unplanned messages. The normal authority is a fully expanded Tag
   Assistant API Call; a proven document-start recorder is conditional stronger
   evidence. The accumulated Data Layer tab is never source authority.
3. `gtm`: current Preview/container identity, matching event, resolved state, concerned
   Data Layer tab, Variables tab, tag inventory/configuration/effective mapping/controls
   and firing count.
4. `delivery`: runtime parameter and logical-hit identity, decoded destination request,
   redirect/retry lifecycle and outcome, or complete-window non-send.
5. `behavior`: duplicate, missing, premature, delayed or interjected events; stale or
   contaminating state; source/Preview/tag/request count and context discrepancies.
6. `safety`: recursive sensitive-data findings in persisted evidence and outputs.

The evidence-confidence gate asks whether each required surface is complete, current and
attributable to the same action/document/Preview epoch. The scenario-completeness gate
asks whether all known material branches are closed. A missing surface blocks only the
claims that depend on it.

## Comparison and causal rules

- Preserve strict JSON semantics: booleans are not numbers; missing, undefined, null,
  empty and populated are different states.
- Allow wire-format coercion only in a transport claim that declares it.
- Attribute observations by browser target, frame/document, route, action, Preview epoch,
  event, tag, logical hit and transport attempt. Never assign an unbound row merely
  because an action is currently open.
- Reject capture timestamps that predate the action instead of trusting a newly supplied
  action ID. Keep between-action unbound deltas in the continuous anomaly stream.
- For a proved navigation/reload, the before page may belong to the old document while
  occurrence evidence belongs to the explicitly rebound new document. Mixed post-action
  documents or an unbound transition remain `BLOCKED`.
- Merge retries/redirects for one logical hit but keep duplicate logical hits separate.
- A settled complete exact source window proves a required event missing (`FAIL`); an
  incomplete API Call/event list or late, partial, or truncated recorder is `BLOCKED`.
- Missing runtime/request data under complete applicable capture is `FAIL`; incomplete
  parameter/body capture is `BLOCKED`.
- A dead/soft-404 page, failed form, unconfirmed purchase, or populated cart represented
  as empty cannot pass because technical surfaces agree.
- Unplanned source/state pushes are inspected between action boundaries. Flag only
  material unexpected, duplicate, premature, delayed, wrong-context or contaminating
  behavior; routine lifecycle/state noise can be classified without failing the event.

## Status and roll-up

- `PASS`: direct current-run evidence proves the applicable accepted claim.
- `FAIL`: settled direct evidence contradicts it.
- `BLOCKED`: an evidenced execution or observability limitation prevents judgement.
- `REVIEW`: one precise verdict-changing semantic ambiguity remains.
- `NOT_APPLICABLE`: evidence proves the applicability predicate false.
- `PENDING`: the action, synchronization or scenario work is unfinished.

Roll-up precedence is `FAIL` > `BLOCKED` > `REVIEW` > `PENDING` > `PASS` >
`NOT_APPLICABLE`. A definite failure is not softened because another check is blocked.
Technical delivery is visible separately but cannot override reality, behavior,
confidence or coverage.

## Immediate pulse and canonical feedback

`commit` emits a compact pulse with action outcome, every currently applicable
operational row/status, notable anomalies, and what still awaits Preview or scenario
closure. It is deliberately
provisional and cannot contain a certified pass.

When an event closes, render two levels from the same canonical result:

1. one compact row per material scenario/signature, then a six-domain event summary;
2. operational rows for every applicable proof target.

Each operational row contains scenario, domain, target (for example DataLayer API, GTM
Preview event, accumulated Data Layer state, resolved variable, named tag
configuration/effective mapping/firing/runtime, browser request/destination, reality
anchor, anomaly, safety or gate), status, observed and expected detail, `Check next`, and
stable evidence IDs. Identical passing rows may be grouped; all differing and non-pass
rows remain scenario-specific. No event may move on without making every applicable
layer status visible; conditional layers remain explicit through applicability or
`NOT_APPLICABLE` reasoning rather than silent omission.

Feedback lists concerned tags, occurrence/count, tested values/signatures, plan gaps,
limitations and exact retest actions. Late journey anomalies may amend an earlier event.

## Finalization and reports

`finish` reconciles all compiled obligations, material branches, unclassified
source/network/Preview observations, protected handoffs, identity/confidence gaps and
privacy findings. It refuses non-final events and renders reports once. A completed run
may contain honest `FAIL`, `BLOCKED` or `REVIEW`; it must not remain open merely because
unobtainable evidence cannot become pass.

Deliver:

- plan-ordered `conclusion.md` and canonical `results.json`;
- validated `results.xlsx` with conclusion, event/domain/operational details,
  requirements, scenarios/coverage, anomalies, tags/delivery, defects/retests,
  limitations and telemetry;
- concise CSV/sidecar views where generated.

Outputs must be formula-safe and privacy-safe. Privacy findings are action-scoped; a
network finding applies to an event only when it belongs to that event's concerned
logical send. An unrelated background request remains redacted evidence but cannot create
a false event failure. `report` may rebuild only from a frozen canonical run; `reopen`
records explicit authorization before any revision.
