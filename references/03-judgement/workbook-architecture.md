# Workbook Architecture

Use `scripts/build_recette_report.py` with normalized JSON and `--strict`.

The workbook contains:

- `Summary`: a compact run status and count overview.
- `Validation Matrix`: the first and active worksheet and the primary deliverable. One row combines dataLayer
  event, tag name, tracking-plan value, observed dataLayer value, tag
  configuration or resolved value, verdict, mismatch, and evidence.
- `Event Evidence`: API-call and resolved Data Layer evidence kept separate.
- `Evidence`: evidence catalogue and links.
- `Run Context`: minimal execution metadata.

Normalized results use `run`, `journeys`, `checks`, `events`, `tags`,
`consent_checks`, `unexpected`, `evidence`, and required `comparisons`.
Use `comparisons` for the displayed validation matrix. Preserve objects and
arrays as serialized structured values rather than flattening away detail.

Use statuses `PASS`, `FAIL`, `BLOCKED`, `REVIEW`, and `NOT_TESTED`. Every result
row needs evidence. A wanted tag with expected status `fired` and actual status
other than `fired` needs a non-firing reason and reason source.
