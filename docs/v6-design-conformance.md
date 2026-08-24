# v6 Design Conformance

Status: pre-release implementation review, 2026-08-24.

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

1. Compile the tracking plan while the configured Playwright MCP server starts.
2. Verify the pinned runtime, headed Edge channel, persistent profile and callable tools
   once.
3. Call `next` before Preview opens the target. For Core, Preview's target opening is the
   one measured navigation; there are no routine cleanup reloads.
4. Perform exactly one semantic action from the frozen card.
5. Read the new Preview indexes once, then deep-read only the planned or suspicious rows
   and concerned tags.
6. Call `complete` once with its exact action ID and one typed action/Preview bundle,
   including continuous deltas since the prior committed boundary.
7. Emit deterministic per-event, per-scenario and per-layer feedback immediately;
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
| Standard browser control | Playwright MCP is the default, pinned to one headed persistent `msedge` profile; existing-window attachment is explicit fallback only. | Runtime/provider/version/channel/profile/headed tests and release pilot gate. |
| First inspection without setup reloads | `next` needs only runtime capability and cumulative target-operation baseline before Preview creates the target load. | First-action test records one action and no automatic repeat. |
| Low agent choice | Public browser loop is `next` then `complete`; low-level begin/commit/sync routes are internal. The action ID and event slice are frozen. | Exact public-command and event-slice regressions. |
| Safe action execution | Cards allow observe, one navigation or one interaction, with explicit document policy. Extra target navigation/reload preserves evidence but blocks confidence. | Unauthorized reload and valid navigation/rebind tests. |
| Loss-aware plan intake | One compiler accepts supported JSON/YAML/tabular inputs, preserves source coordinates and types, excludes code examples, and localizes later-event errors. | Flat/two-block/merged workbooks, ignored rows, orphan rows and malformed later events. |
| Correct source authority | Expanded API Call is the normal exact-message source; accumulated Data Layer remains post-message state. A recorder is conditional. | Source laundering, late recorder and API Call fallback tests. |
| Plan-first field coverage | Every applicable plan predicate is projected independently to source, state, Variables, mapping, runtime and request. | Partial-tag, missing runtime and missing request-field regressions. |
| Human-like anomaly detection | Every intervening source message is retained without relabelling between-action rows; the following completion immediately revises an affected prior event. | Duplicate/missing/interjected, public between-action revision, stale-history rejection, stale cart/item, dead page, form, media and repeated-purchase tests. |
| Material scenario depth | Finite values are exhausted, dependent values use reachable combinations, and high-cardinality members use adaptive behavior signatures. | Language, shipping dependency, product signature, plan-gap and coverage-reopen tests. |
| Targeted GTM work | One event-list delta is read per action; only concerned or suspicious rows/tags are deep-read. Exact-message tabs stay separate from later Trigger Group evidence. | Delayed technical-row join and exact-row non-substitution tests. |
| Trustworthy output | One renderer owns statuses and emits scenario/domain summaries plus every applicable operational row, reason, expected/observed, check-next and evidence. | Compact/full feedback, report, freeze and formula-safety tests. |
| Real-life release protection | A tagged release requires a clean Playwright pilot with Core and an ordinary event, one Preview pass, complete mandatory layers and latency/operation limits. | `check_release.py --tag ... --live-pilot ...`; synthetic fixtures cannot satisfy this gate. |

## Quality-preserving speed decisions

- Compile and start Playwright concurrently.
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
- Fast-fail an invalid runtime contract before an action rather than probing alternatives.

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
