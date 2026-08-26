# GTM Client Recette

Repository version: **v13.0.0**.

This personal Codex skill executes one GA4 client-side GTM acceptance recette from one
imperfect, variably structured XLSX. It tests one representative live scenario per
identifiable event through five fixed evidence layers and produces one final XLSX.

## Fixed path

- Input: an XLSX filename, absolute path, or bounded location description, then `ready`
  and `prepared`; GA4 client-tag scope is intrinsic and needs no confirmation phrase.
- Browser: one headed Playwright MCP browser containing the target site and connected
  Tag Assistant Preview. Production never uses a direct Python Playwright browser.
- Coverage: one scenario per identifiable event in workbook order.
- Output: one canonical workspace `inspection-plan.json`, immediate five-layer feedback,
  and one `gtm-client-recette-results.xlsx`.
- No modes, retries, fallback evidence, backup, generated browser-control JavaScript,
  GTM mutation, or publication.
- Native MCP text is parsed through one long-lived in-memory bridge. It is never saved as
  raw snapshot, network, DOM, Base64, or duplicate mapping files.

## Imperfect plans

The workbook is extracted once. Supported `dataLayer.push` and `gtag` code is parsed as
text and never evaluated. One interpreter handles irregular tables and images; deterministic
validation reconstructs table semantics from a complete Data Layer payload or reconstructs
the payload from event/parameter/value rows. Both forms must reconcile when both exist.
Missing definitions, triggers, URLs, screenshots, destinations, types, or requiredness become
cited review notices rather than fatal ingestion errors.
Generic value/example columns are presence-and-type evidence only; exact equality or finite
allowed values require an explicit workbook header declaring that meaning.

For every event, the fixed ScenarioResolver returns one target, the shortest finite necessary setup sequence,
and one measured action. A supplied plan URL is exact. Otherwise the target is resolved
adaptively on the already prepared site origin. Setup happens before the Tag Assistant
cursor fence; only the measured action is attributed. An unresolved event is committed as
`BLOCKED`, and the next event continues.

## Evidence

Every event reports exactly, in order:

1. Page/action reality
2. Data Layer API Call
3. GTM Tags
4. Browser request
5. Surrounding behavior

The target page receives exactly one before and one after screenshot per event. Tag Assistant
is inspected through native MCP accessibility text only. Fixed Python parsers select the
candidate API Call and bounded causal tag rows; Tag Assistant screenshots and image reading
are prohibited. The inaccessible API Call chevron is expanded by one immutable Playwright
right-edge click that verifies one collapsed card before the click and one expanded card after.

See [`SKILL.md`](SKILL.md) and [`references/contracts.md`](references/contracts.md) for
the executable workflow and schemas.

## Verification

```powershell
python -B scripts/run_tests.py
python -m ruff check scripts tests
python -m ruff format --check scripts tests
python -m vulture scripts tests --min-confidence 80
```

The representative-workbook extraction/authority forward test passes. A connected Tag
Assistant smoke run reaching the final workbook without code changes or retries remains
required before calling the runtime operationally proven.
