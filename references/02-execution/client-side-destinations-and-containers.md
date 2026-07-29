# Client-Side Destinations And Containers

## Vendor-neutral acceptance model

Treat the tracking plan or explicit acceptance rule as the source of truth.
Vendor profiles help decode browser evidence; they do not add, rename, or
remove client requirements.

Supported client-side vendor families are:

- `ga4`;
- `google_ads`;
- `floodlight`;
- `meta`;
- `linkedin`;
- `tiktok`;
- `pinterest`;
- `microsoft_ads`;
- `x_ads`;
- `custom`.

Use one atomic requirement per concerned tag, destination ID, and parameter.
When one event must reach two GA4 measurement IDs, two pixels, or an analytics
and media destination, keep separate rows under the same event group. This
makes a partial delivery visible.

Declare `tag_delivery` before execution:

- `browser_request` for a tag whose accepted client-side effect is an
  analytics/media request;
- `local_only` for a genuinely local tag whose accepted effect has no browser
  send.

Do not infer local-only merely because Preview hides a value. A fired
browser-sending tag always requires a same-action first-party network check.

For each destination normalize:

- vendor family and tag/template type;
- owning client-side container;
- exact destination, measurement, pixel, partner, conversion, or activity ID
  prescribed by the acceptance source;
- exact vendor-facing event/conversion name prescribed by the acceptance
  source;
- expected browser-request behaviour: `sent`, `sent_once`, `absent`, `blocked`,
  `cookieless`, or `full`;
- accepted endpoint pattern;
- raw browser-request paths for the destination ID, vendor event name, and
  tested outbound parameter, plus the decoded value and type;
- expected request count when duplication matters.
- stable browser `request_id` or capture-record ID tied to the action and
  owning client container.

Common vendor identifiers and names are only decoding hints:

| Family | Typical acceptance evidence |
| --- | --- |
| GA4 | measurement/destination ID, event name, `send_to`, event and item parameters |
| Google Ads | conversion ID, conversion label, value, currency, transaction ID |
| Floodlight | advertiser/configuration, activity group/tag, activity, counting method, custom variables |
| Meta | pixel ID, standard/custom event, event parameters |
| LinkedIn | partner or conversion ID and conversion payload |
| TikTok | pixel ID, event name, properties |
| Pinterest | tag ID, event name, event data |
| Microsoft Ads | UET tag ID, event action/category/label or custom-event fields |
| X Ads | pixel/event ID and event parameters |
| Custom | accepted endpoint/call contract and exact payload |

Resolve precise names and required fields from the supplied plan and current
official vendor documentation. Never silently translate a GA4 field into a
media field. Record the explicit mapping in each vendor-specific requirement.

## Evidence order

Use the smallest authoritative combination:

1. GTM Preview/Tag Assistant proves which concerned tag fired, did not fire, or
   errored and shows its resolved inputs.
2. First-party browser-network capture proves the browser attempted the
   request, endpoint, destination ID, request count, and decoded parameter.
3. Browser console evidence explains a direct-library or Custom HTML error.
4. A vendor helper or vendor UI is supplementary confirmation only.

Never claim that a browser request proves vendor receipt, processing,
deduplication, attribution, reporting, or audience membership. Those need a
separate acceptance source and appropriate vendor-side access.

Normalize request evidence in `destination_request` with
`capture_source: browser_network` and a stable `request_id`. A `PASS` request cannot rely solely on
`vendor_helper`. Use paths rooted at `query.`, `body.`, or `headers.` so the
validator can reconcile each decoded claim with the retained browser request:

```json
{
  "destination_id_parameter_path": "query.id",
  "destination_event_parameter_path": "query.ev",
  "destination_parameter_path": "query.value"
}
```

The destination ID, vendor event name, and parameter value/type must match
both the tracking-plan expectation and their exact raw request locations.
Repeated query keys remain arrays and cannot silently pass as one scalar. A
declared destination or destination parameter requires its component verdict;
removing the verdict cannot preserve an overall `PASS`.

Use the context-level capture procedure in
[interaction-and-capture-playbook.md](interaction-and-capture-playbook.md) and
decode retained requests with `scripts/decode_browser_requests.py`. Keep
navigation/unload sends, redirects, new tabs, service-worker ownership, and
newline-delimited batches attributable to their exact action window. Treat a
first-party `transport_url` endpoint as a client-visible destination variant;
do not inspect or certify the server container behind it.

Use quoted bracket keys when a literal vendor key contains dots, brackets, or
other path syntax:

```json
{
  "ga4_event_parameter": "query[\"ep.value\"]",
  "meta_custom_data": "query[\"cd[value]\"]"
}
```

Unquoted `query.ep.value` means nested objects; it does not mean the literal
query key `ep.value`. Numeric indexes use `[0]`, and `[]` remains an array
wildcard for declarative payload paths.

## Custom HTML and direct calls

For a Custom HTML tag or direct library call:

- preserve the actual signal source as `custom_html` or
  `direct_vendor_call`;
- capture the Preview firing state when GTM owns the tag;
- capture direct console exceptions and returned `undefined` values;
- capture the outbound request or accepted client-side side effect;
- do not fabricate a `dataLayer.push` when none occurred.

If Custom HTML executes code but no accepted request or side effect appears,
separate tag-firing `PASS` from destination or runtime `FAIL`.

## Multiple web containers

Inventory every loaded client-side web container before testing. `run.containers`
is required even for a single container. Record stable
container ID, workspace, role, Preview environment, and version when visible.
Assign exactly one owner to each concerned tag requirement.

Use roles:

- `primary`;
- `analytics`;
- `marketing`;
- `shared`.

If two containers both own or fire the same accepted destination, record a
`container_conflict` client check and relevant unexpected duplicate. Do not
build an event-by-every-tag matrix.

When multiple simultaneous Preview connections are unreliable:

1. checkpoint the website and consent state;
2. preview the first web container and capture its event cursor/evidence;
3. return to the same reproducible checkpoint;
4. preview the next web container and repeat;
5. keep container-specific evidence separate.

Server containers, server clients, transformations, outbound server requests,
and browser/server deduplication are outside this skill.

## Google and GA4 profile notes

Use current official documentation when the plan adopts vendor-recommended
semantics:

- [GA4 recommended events](https://developers.google.com/analytics/devguides/collection/ga4/reference/events)
- [GA4 ecommerce measurement](https://developers.google.com/analytics/devguides/collection/ga4/ecommerce)
- [Validate GA4 ecommerce](https://developers.google.com/analytics/devguides/collection/ga4/validate-ecommerce)
- [Google Ads conversions in GTM](https://support.google.com/tagmanager/answer/6105160)

For multiple GA4 destinations, validate the actual destination ID or `send_to`
for each atomic row. DebugView is supplementary and must not replace Preview
and browser-request evidence.

When a GA4 tag uses **Send ecommerce data** from the Data Layer, the option may
not expose individual values in static tag configuration. Validate the layers
separately:

1. exact configured ecommerce source/option;
2. raw ecommerce API Call and resolved ecommerce state at that event;
3. each applicable GTM or Custom JavaScript input and exact type;
4. fired tag count and runtime event/ecommerce values;
5. decoded GA4 request event name, destination ID, and applicable event/item
   parameters.

The option being configured does not prove the resolved ecommerce values; the
request being correct does not repair a wrong raw or runtime value.
