# Client-Side Runtime Contexts

Use `run.browser_contexts` for stable viewport and user-state definitions and
`requirement.client_checks` for acceptance-relevant runtime observations. A
check needs an ID, category, comparison, expected value, actual value, status,
and evidence ID.

## SPA navigation and auto-event sources

For each SPA requirement distinguish:

- initial document load;
- `history.pushState`;
- `history.replaceState`;
- `popstate`;
- hash or same-document change;
- route rendering without navigation.

Record whether the accepted signal came from:

- an explicit `dataLayer.push`;
- a GTM native lifecycle or auto-event;
- a DOM event;
- GA4 enhanced measurement;
- a direct vendor call.

Do not treat a GA4 enhanced-measurement event as proof that the planned
dataLayer event occurred. Test duplicate prevention across route changes and
keep action ID, event index, signal source, and timestamp.

## Responsive and user contexts

Define each required desktop, mobile, tablet, authenticated, anonymous,
personalized, or A/B context with:

- stable `context_id`;
- device class;
- exact viewport width and height;
- relevant user state;
- acquired variant.

Repeat the journey in each accepted context when selectors, visible elements,
values, or firing behaviour differ. Responsive selectors are not interchangeable
evidence.

## Cross-domain, cookies, linker, and iframes

When the acceptance rule requires them, record separate checks for:

- cookie domain and relevant cookie creation/read behaviour;
- accepted cross-domain linker parameter on the actual outbound link;
- preservation through redirects;
- new-domain Preview connection and event continuity;
- first-party versus third-party iframe ownership;
- iframe-to-parent or parent-to-iframe messaging used by the implementation.

Do not expose full cookie values or identifiers in evidence. Store presence,
domain/path/flags, redacted structure, and evidence.

## dataLayer integrity

Use the runtime-semantic procedure and supplemental recorder in
[interaction-and-capture-playbook.md](interaction-and-capture-playbook.md).
Detect and record:

- the initial `window.dataLayer` type;
- whether `.push` remains callable;
- reassignment after GTM boot;
- multiple incompatible layer names;
- replacement of the array rather than appending;
- legacy object initialization mixed with array pushes;
- loss of queued messages during navigation.
- stale recursive object/array state and ghost ecommerce items;
- missing prescribed ecommerce clearing;
- payload-object reuse or mutation;
- multiple arguments in one push, event callbacks/timeouts, and relevant
  `gtm.uniqueEventId` chronology.

A later resolved value cannot repair a missing raw push. A dataLayer reset is a
`data_layer_integrity` failure only when it contradicts the acceptance rule or
explains a confirmed loss.

## Custom JavaScript and tag dependencies

For Custom JavaScript variables and Custom HTML:

- retain exact returned state and type, including `undefined`;
- capture direct Preview or console error text as evidence;
- separate variable failure, tag firing, and outbound request verdicts;
- never infer that a tag succeeded merely because its container reports
  `Fired`.

Represent setup/main/cleanup order in `sequence_contract` and
`tag_sequence.actual_order`. Represent other prerequisites as
`tag_dependency` checks.

## Platform adapters

Shopify, Magento, WooCommerce, and other platform conventions may help locate
the relevant client signal. Record the observed convention and the explicit
mapping to the tracking-plan field.

Never let a plugin or platform convention become the acceptance source. If its
meaning is ambiguous, use `REVIEW`.

## Debug mode and vendor helpers

Record `debug_mode` as a client check when prescribed. Record GA4 DebugView or
another vendor UI as `debugview` or supplementary vendor evidence.

Vendor-side visibility can lag or be sampled. It does not replace deterministic
Preview and network evidence unless the explicit acceptance rule is vendor-side
receipt and the required access is available.

## Current client-side limits

Do not hardcode volatile vendor quotas in the skill. When a limit check is
required:

1. resolve the current threshold from official documentation;
2. record the documentation URL/date or other `limit_source`;
3. capture the current count or payload size;
4. use `maximum` for a confirmed threshold;
5. use `warning_only` and `REVIEW` when proximity is operationally relevant but
   not an acceptance failure.

Examples include parameter counts, payload size, event-name inventory,
user-property counts, vendor activity limits, and request-rate warnings.
