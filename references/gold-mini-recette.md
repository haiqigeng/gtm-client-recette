# Gold Mini Recette

This synthetic example demonstrates the canonical operating shape. It is not a
client plan and must never become an acceptance source for another website.

## Tracking-plan excerpt

| Order | Event | Interaction | Requirement |
| --- | --- | --- | --- |
| 1 | `view_item_list` | Open `/products` | Fire once on the product-list page with `item_list_name="catalogue"` |
| 2 | `add_to_cart` | Click both visible product cards | One push and one GA4 tag per click; `price` is a number in raw, variable, runtime and request |
| 3 | `generate_lead` | Complete test form | Submit with synthetic data; tag and request fire once |

## Case census

```json
[
  {
    "event_group_id": "EVG-001",
    "cases": ["load:/products"]
  },
  {
    "event_group_id": "EVG-002",
    "cases": ["card:alpha", "card:beta"]
  },
  {
    "event_group_id": "EVG-003",
    "cases": ["synthetic-lead:standard"]
  }
]
```

## Controlled observations

The run uses `analytics_only`. Before each action, Tag Assistant inventory finds
the concerned GA4 tag and one unrelated Meta tag; the Meta tag remains visible
as `OUT_OF_SCOPE`. The complete applicability card is frozen before execution.

1. Opening the homepage before `/products` unexpectedly pushes
   `view_item_list` with `item_list_name="homepage"`.
2. `/products` pushes the expected list event once.
3. Both card clicks push correct numeric prices.
4. The GA4 tag fires once for each card, but the second card resolves its
   runtime price as string `"29.90"`.
5. The lead journey completes with an approved synthetic profile and produces
   one tag and one browser request.

## Judgement

```text
Event 01 — view_item_list: FAIL
- Expected listing-page occurrence is correct.
- An additional wrong-context homepage occurrence was observed and retained.

Event 02 — add_to_cart: FAIL
- Cases: 2/2 executed.
- raw_api_call: PASS for both.
- resolved_data_layer: PASS for both.
- GA4 - add_to_cart / tag_configuration: PASS.
- GA4 - add_to_cart / tag_firing: PASS once per action.
- GA4 - add_to_cart / tag_parameter: FAIL on card:beta; expected number 29.90; observed string "29.90".
- GA4 - add_to_cart / browser request: FAIL on card:beta for the same type mismatch.
- Meta - AddToCart: OUT_OF_SCOPE — detected outside analytics-only scope.

Event 03 — generate_lead: PASS
- Synthetic journey submitted.
- Every canonical layer and each GA4 tag subrow is explicit and PASS or an
  evidenced conditional NOT_APPLICABLE.
```

The `add_to_cart` result illustrates the dependency rule: a correct raw
dataLayer value and a fired tag do not make a wrong runtime tag value pass.
The `view_item_list` result illustrates whole-stream reconciliation: the event
is planned, but its incompatible homepage occurrence still fails.

## Normalized shape

Each event is represented by source-bound requirement rows. The second event
has separate component verdicts, while the session ledger additionally retains
one row per canonical layer and each in-scope tag/layer pair:

```json
{
  "verdict": {
    "event_occurrence": "PASS",
    "raw_payload": "PASS",
    "resolved_data_layer": "PASS",
    "gtm_variable": "PASS",
    "tag_configuration": "PASS",
    "tag_firing": "PASS",
    "tag_parameter": "FAIL",
    "destination_request": "FAIL",
    "overall": "FAIL",
    "failure_layer": "tag_parameter",
    "mismatch": "card:beta price expected number 29.90; observed string \"29.90\""
  }
}
```

Use `tests/fixtures/valid_full.json` as the machine-validated single-event
schema example. Use `tests/fixtures/client_side_extension.json` for the
machine-validated destination, trigger, sequence, consent, business/privacy
and browser-context extensions. Generate the workbook only through the strict
builder; do not commit generated client artifacts.
