# v6 Design Conformance

Status: v6.0.1 release review, 2026-08-24.

## Decision

The deterministic implementation conforms to the Playwright-first target architecture.
It is a general control-path redesign: no client, domain, workbook, event count,
container, destination, selector, or prior run is embedded.

The remaining acceptance gate is a clean live pilot through the configured Playwright
MCP server. Local tests prove the engine and workflow contracts; they cannot prove real
Tag Assistant panel latency or a third-party website's behavior.

## North star

Maximize trustworthy findings per expensive browser interaction. One event does not pass
because a source message exists or a tag fired. The same material scenario must support
an attributable chain from business reality through source, GTM decision, runtime and
browser delivery, while the complete surrounding stream remains available for anomaly
analysis.

## Default operating path

1. Ask one minimal intake and, after `ready`, open a blank managed Edge window immediately.
2. Compile/reconcile the plan while the user prepares authentication, Preview, site and
   ordinary consent in that same window.
3. Verify the capability-based runtime and prepared identities once. If consent required
   a setup page, call `next` before exactly one measured Core reload; otherwise call
   `next` before final Connect/target navigation.
4. Perform exactly one semantic action from the frozen card.
5. Read only Preview indexes after the frozen epoch/index cursor, then deep-read planned or suspicious rows
   and concerned tags.
6. Call `complete` once with its exact action ID and one typed action/Preview bundle,
   including continuous deltas since the prior committed boundary.
7. Emit deterministic compact per-event/per-layer feedback immediately even when
   scenario closure is pending;
   timestamped between-action evidence revises the affected prior event in that pass.
8. Repeat for the next interaction or material scenario, then finalize once.

One interaction may create several technical Preview rows or satisfy several causally
co-occurring claims. It never authorizes a second user interaction before `complete`.

## Applicable inspection chain

For an ordinary planned browser-sending event, the same action can support these
separate checks:

1. page, action and independent business reality;
2. exact expanded Tag Assistant API Call, or conditional proven invocation-time source;
3. Tag Assistant accumulated Data Layer state;
4. Tag Assistant Variables;
5. matching GTM event and complete concerned fired/not-fired inventory;
6. each concerned tag's configuration, effective mapping, controls, firing count and
   event-time runtime payload;
7. decoded logical browser request, destination and transport outcome;
8. complete surrounding source/network chronology and anomaly checks;
9. safety, evidence confidence and material-scenario coverage.

These are applicable proof surfaces, not serial browser phases. Source-only and
state-only requirements do not inherit invented tag or request obligations. Consent,
acquisition, forms, media, sequencing and protected handoffs activate only when relevant.

## Design-to-implementation crosswalk

| Required behavior | Implemented design | Verification |
| --- | --- | --- |
| Standard browser control | Playwright MCP is the default in one headed persistent `msedge` profile; behavior is capability-based rather than package-version-pinned. Existing-window attachment is explicit fallback only. | Runtime/provider/channel/profile/headed and missing-capability tests plus release pilot gate. |
| First inspection without cleanup loops | Browser preparation overlaps plan compilation. `next` needs only runtime capability and optional health before one attributable Core load. | First-action and unavailable-surface tests record one action and no automatic repeat. |
| Low agent choice | Public browser loop is `next` then `complete`; low-level begin/commit/sync routes are internal. The action ID and event slice are frozen. | Exact public-command and event-slice regressions. |
| Safe action execution | Cards allow observe, one navigation or one interaction, with explicit document policy. Extra target navigation/reload preserves evidence but blocks confidence. | Unauthorized reload and valid navigation/rebind tests. |
| Loss-aware plan intake | One compiler accepts supported JSON/YAML/tabular inputs, preserves exact machine case/coordinates/types, continues sectioned tables across blanks, classifies every sheet, reconciles index/detail events, excludes code, and localizes later-event errors. | Flat/two-block/merged/blank-separated workbooks, sheet manifest/reconciliation, ignored rows, orphan rows and malformed later events. |
| Correct source authority | Expanded API Call is the normal exact-message source; accumulated Data Layer remains post-message state. A recorder is conditional and direct/Preview occurrences reconcile one to one. | Source laundering, late recorder, fallback and identical-duplicate tests. |
| Plan-first field coverage | Every applicable plan predicate is projected independently to source, state, Variables, mapping, runtime and request. | Partial-tag, missing runtime and missing request-field regressions. |
| Human-like anomaly detection | Every intervening source message is retained without relabelling between-action rows; the following completion immediately revises an affected prior event. | Duplicate/missing/interjected, public between-action revision, stale-history rejection, stale cart/item, dead page, form, media and repeated-purchase tests. |
| Material scenario depth | Finite values are exhausted, dependent values use reachable combinations, compiler-known dimensions/constraints cannot be weakened, singleton is explicit, and high-cardinality contrast is required only for a distinct signature. | Language, shipping, constraint-preservation, singleton, one-signature product, plan-gap and coverage-reopen tests. |
| Targeted GTM work | One cursor-bounded event-list delta is read per action; only concerned/suspicious rows/tags are deep-read. Exact source occurrence, accumulated state and later Trigger Group evidence remain separate. | Cursor/history, API Call preservation, delayed technical-row join and exact-row tests. |
| Trustworthy output | One renderer owns statuses and emits immediate compact operational-layer rows while preserving every detailed claim in JSON/XLSX. Coverage errors remain visible without blocking capture. | Compact/full feedback, incomplete-coverage, report, freeze and formula-safety tests. |
| Correct setup attribution | Wrong binding and accidentally denied ordinary consent block dependent layers rather than creating client failures; explicit denied consent needs complete suppression proof. | Binding cascade and ordinary/explicit consent regressions. |
| Real-life release protection | A tagged release requires a clean Playwright pilot with Core and an ordinary event, one Preview pass, complete mandatory layers and latency/operation limits. | `check_release.py --tag ... --live-pilot ...`; synthetic fixtures cannot satisfy this gate. |

## Quality-preserving speed decisions

- Open the managed browser after readiness, then compile while the user prepares it.
- Do not pre-create all scenario cases, layer rows, tag inventories or reports.
- Use API Call normally and install a document-start recorder only for a dependent claim.
- Reuse one managed window, target tab, Preview tab, container/workspace identity and
  continuous collectors.
- Complete after each real interaction; batch only the technical rows caused by it.
- Deep-read current planned fields, concerned tags and suspicious rows, not historical
  domains or the whole container.
- Build the occurrence model once per completion batch and reuse it for every included
  claim.
- Render compact checkpoints during the run and full artifacts only at finalization.
- Freeze a Preview cursor per action instead of rescanning historical events.
- Fast-fail an invalid runtime identity; convert unavailable evidence surfaces to targeted
  blocks rather than probing alternatives.

None of these decisions removes a required proof surface or scenario. They reduce
handshakes, repeated UI traversal and premature bookkeeping.

## Machinery deliberately absent

- browser-extension dependency on the normal path;
- Firefox or cross-browser abstraction for this personal skill;
- browser replacement, coordinate clicking or guessed-tool recovery;
- two clean Core reloads, automatic retest or generic slow mode;
- fixed event/layer counts or whole-plan frozen scenario scaffolds;
- global container/tag inventories and unrelated historical-domain scans;
- a second result ledger, database, worker, service or telemetry platform;
- arbitrary scenario caps, full product enumeration or global Cartesian products;
- one evidence file per layer or one model pass per field;
- client/run-specific normalizers, paths, selectors or repair branches.

## Progressive-disclosure check

The instruction order now exposes each prerequisite at its first point of use:

1. authority/readiness before opening the browser;
2. browser guide before managed-window preparation;
3. plan reconciliation before any event selection;
4. capability, prepared identities and ordinary consent before `next`;
5. scenario guide immediately before branch selection;
6. protected-journey guide only when triggered;
7. verdict guide before the first `complete`;
8. coverage expansion only after current evidence reveals a branch;
9. final reporting only after closure.

No expected URL/container question, exact MCP pin, tag inventory, future scenario matrix,
manual counter baseline, or report scaffold is discovered late because none is a normal
startup prerequisite.

## Conformance verdict

| Area | Verdict |
| --- | --- |
| Playwright-first workflow | CONFORMS |
| Plan normalization and typed claims | CONFORMS |
| Inspection depth and source separation | CONFORMS |
| Cross-layer plan comparison | CONFORMS |
| Anomaly and business-reality judgement | CONFORMS |
| Scenario variability | CONFORMS |
| Per-event/per-layer output | CONFORMS |
| Repository generality and hygiene | CONFORMS |
| Clean live Playwright/Tag Assistant pilot | PENDING |
