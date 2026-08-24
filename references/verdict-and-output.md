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
contiguous flat table; a blank separator resets that identity. In a recognized sectioned
variable sheet, blank rows do not terminate the variable table. XLSX intake classifies
every sheet and reconciles index events with requirement sheets. Index-only or malformed
later events become localized non-executable events; orphan/ambiguous rows still stop
intake. Preserve exact case for valid machine event/field identifiers. Do not silently
reinterpret a rule or invent missing tag scope. A source-only/state-only claim remains
source-oriented. For ordinary GA4 claims, the same
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
  action ID. Start `next` before the Preview connection's first measured load; keep
  between-action unbound deltas in the continuous anomaly stream.
- Consume Preview by epoch/index cursor. One completion may contain only indexes after
  the frozen boundary; a new epoch must start at zero with a matching rebound identity.
  This prevents historical session scans from becoming current evidence.
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
- When ordinary consent is accidentally denied, tag/delivery rows are setup `BLOCKED`
  with an instruction to accept the CMP; do not report client failures from that context.
  An explicitly denied-consent scenario passes suppression only when fired/non-fired and
  request windows are complete. Runtime/request values then become `NOT_APPLICABLE`.
- A wrong or unattributable origin/container/Preview binding blocks every dependent
  source/GTM/delivery/behavior claim. It does not manufacture downstream client failures.

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

## One-pass canonical feedback

`complete` is the one-pass checkpoint. It commits action deltas, ingests the one bounded
Preview delta, builds the causal model once, and emits canonical feedback immediately.
If it is interrupted after the commit record, rerunning the same action ID and bundle
resumes synchronization without another browser action.

The continuous delta may begin at the prior committed boundary. Timestamped rows before
the current action stay unbound and can revise the immediately preceding event in this
same model pass; they are never relabelled as current-action evidence.

After every completed action, render two levels from the same canonical result even when
scenario coverage remains pending or contains a closure error:

1. one compact row per material scenario/signature, then a six-domain event summary;
2. compact operational-layer rows, with detailed proof-target rows retained in canonical
   JSON/XLSX.

Each compact layer row shows status, passed/total checks, concise non-pass
observed-versus-expected exceptions, `Check next`, and stable evidence IDs. Detailed rows
retain scenario, domain, exact target (for example DataLayer API, GTM Preview event,
accumulated Data Layer state, resolved variable, named tag configuration/effective
mapping/firing/runtime, browser request/destination, reality anchor, anomaly, safety or
gate), status, observed, expected, reason and evidence. Identical passing rows may be
grouped; all differing and non-pass rows remain scenario-specific. Conditional layers
remain explicit through applicability or `NOT_APPLICABLE` reasoning rather than silent
omission. An action-card violation is an
operator-protocol `BLOCKED` row: useful client evidence remains, no client `FAIL` is
invented, and no automatic repeat starts.

Feedback lists concerned tags, occurrence/count, tested values/signatures, plan gaps,
limitations and exact retest actions. Late journey anomalies may amend an earlier event.
An incomplete coverage annotation is persisted and shown as `PENDING`/`BLOCKED`; it does
not roll back machine evidence or suppress immediate feedback. A committed
evidence-defect retest supersedes its referenced bad action only when the event slice and
scenario are identical; user-request retests do not erase prior evidence.

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
