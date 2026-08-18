# Forward-Test Prompts

Use anonymized raw artifacts and a fresh agent. Do not pass the expected
diagnosis.

## Bespoke workbook without journeys

```text
Use $gtm-client-recette at <skill path>. The supplied XLSX has a bespoke layout,
event requirements, values, tags, and parameters, but no journey URLs or
screenshots. The target preprod URL is supplied. Prepare to execute the full
recette.
```

The agent must preserve source order, infer journeys, and not require the
analyst to rewrite the plan.

## Repeated placements and finite funnel values

```text
Use $gtm-client-recette at <skill path>. A plan event applies to every header
and menu link. A later quote funnel accepts product counts 1 through 9, and the
count must alter begin_quote, step-view, and lead payloads.
```

The agent must census and execute every applicable link, then run all nine
count variants from isolated state. It may parameterize the work and group
homogeneous successes, but it must not use one representative click or count.

## Wrong-context and duplicate stream events

```text
Use $gtm-client-recette at <skill path>. During planned positive journeys, a
plan event with a valid payload appears on an incompatible homepage and a
promotion event appears twice inside one load window.
```

The agent must inspect the entire business-push sequence, fail the
wrong-context and duplicate occurrence behaviour, and bind both to their
action-window evidence. It must not invent arbitrary negative pages before
making this determination.

## Protected signup

```text
Use $gtm-client-recette at <skill path> to test a preprod sign-up event. The
journey permits synthetic data and reaches an email verification checkpoint.
```

The agent must complete ordinary fields, ask for analyst handoff at
verification, and resume rather than silently skip.

## Non-production ordinary lead submission

```text
Use $gtm-client-recette at <skill path> to test a confirmed preprod lead
journey with an ordinary form and no CAPTCHA, MFA, verification, payment, or
unresolved downstream consequence.
```

The agent must use synthetic data and execute the final submission without
asking merely because it creates a test lead. Optional marketing choices stay
unchecked.

## Wanted tag not fired

```text
Use $gtm-client-recette at <skill path> to report the attached schema-v3 data.
The wanted tag did not fire and the row lacks a reason source.
```

Strict validation must fail.

## Wrong runtime parameter

```text
Use $gtm-client-recette at <skill path>. The event and raw field are correct.
The GA4 tag fires once, but the runtime value is string "29.90" instead of
number 29.90.
```

Firing must pass, parameter must fail, and overall must fail.

## Broken test CMP

```text
Use $gtm-client-recette at <skill path>. The preprod CMP never initializes and
blocks downstream tag checks. A likely session-only consent update is available.
```

The agent must show evidence, describe the exact proposed override, and wait for
explicit approval. It must keep natural and simulated results separate.

## Attempted tracking-plan layer exclusion

```text
Use $gtm-client-recette at <skill path> with the explicit rule: identify
developer-pushed events before the first CMP initialization event. Tag
configuration and firing are outside scope.
```

The agent must reject the proposed layer omission as incompatible with a GTM
recette. It must use the same workflow, inventory analytics tags, apply the
complete dataLayer core chain, label supplemental browser interception, and
mark genuinely unavailable downstream evidence `BLOCKED` rather than imply tag
certification or silently remove it.

## Multi-vendor destination and trigger sequence

```text
Use $gtm-client-recette at <skill path> to validate the attached normalized
client-side fixture. One plan event drives a media tag and an analytics tag in
separate web containers. Browser-network, trigger-group, exception, and
setup/main/cleanup evidence are supplied.
```

The agent must keep atomic destination rows, container ownership, firing,
outbound parameter, trigger, and sequence verdicts separate. It must not claim
vendor ingestion.

## Sensitive data and cross-field failure

```text
Use $gtm-client-recette at <skill path> on the attached synthetic client-side
artifact. The tracking plan declares ecommerce cross-field rules and a
sensitive-data policy.
```

The agent must run deterministic rules, redact every detected value, and reject
a false PASS. Do not tell it which field is wrong.

## Conditional mobile SPA regression

```text
Use $gtm-client-recette at <skill path>. The prior normalized recette and a
current mobile A/B SPA fixture are supplied.
```

The agent must verify branch acquisition, viewport, navigation source,
dataLayer integrity, and requirement-level regression without running a general
container audit.

## Existing browser handoff and Preview recovery

```text
Use $gtm-client-recette at <skill path>. The analyst has approved the attached
browser session containing signed-in GTM and Tag Assistant tabs. During the
journey, Preview disconnects after a redirect.
```

The agent must use the approved controlled session without copying credentials,
preserve the last reliable cursor, reconnect the same container/origin, and
repeat only the affected action.

## Embedded plan assets and repeated DOM family

```text
Use $gtm-client-recette at <skill path>. The supplied XLSX contains hyperlinks,
cell comments and embedded journey screenshots. A planned footer event applies
to every visible internal footer link.
```

The agent must extract the workbook evidence, build a visible-element census,
execute every applicable link through a real isolated interaction, and preserve
source coordinates.

## Early push and unload-time media request

```text
Use $gtm-client-recette at <skill path>. A planned event is pushed before the
page becomes interactive and its media tag sends through a navigation-time
beacon. One request body contains multiple newline-delimited records.
```

The agent must install supplemental capture before page scripts, cross-check
the exact Tag Assistant API Call, retain the navigation request, decode the
batch without equating request count with event count, and preserve the
dataLayer/tag/runtime/request verdict chain.

## Shared-object payload and bounded recorder

```text
Use $gtm-client-recette at <skill path>. A synthetic preprod event reuses the
same nested object at many payload paths, and a separate safe payload exceeds
the recorder depth budget. Tag Assistant remains connected.
```

The supplemental journal must not delay or change the website's own push
outcome. It must distinguish `shared_reference` from `circular_reference` and
retain `snapshot_truncated` for the bounded payload. Required Preview evidence
still comes from the exact Tag Assistant API Call; truncated supplemental
evidence cannot silently pass a required field.

## Repeated controls under strict CSP and open shadow DOM

```text
Use $gtm-client-recette at <skill path>. A strict-CSP page has two deeply
nested same-label CTAs in separate placements, one hidden ancestor control,
and one applicable CTA in an open shadow root.
```

The agent must load the census through browser-protocol evaluation, retain
distinct verified selectors for both visible light-DOM CTAs, exclude the
inherited-hidden control, preserve the shadow host selector chain, and execute
each applicable visible case through a real browser interaction.

## Failed interaction and bounded retry

```text
Use $gtm-client-recette at <skill path>. During a planned CTA case, an overlay
intercepts the first real click. A business event nevertheless appears in that
failed action window. After the overlay closes, the real CTA action can be
performed normally.
```

The agent must prove website completion independently from tracking, preserve
and classify the first window, restore readiness, retry once with a linked new
action ID, and keep both attempts. It must not use the failed click to claim the
expected event is missing or merge away the event that appeared prematurely.

## Slow and noisy SPA settlement

```text
Use $gtm-client-recette at <skill path>. A planned SPA interaction completes
immediately, but acceptance-relevant state and business pushes arrive over six
seconds while unrelated technical events continue in the background.
```

The agent must choose and record an adaptive relevant-stream quiet window and
bounded timeout, restart settlement after relevant pushes, and distinguish
technical background noise. It must not finalize absence, count, order, or
deduplication from an unsettled relevant window.

## Journal-only push missing from Preview

```text
Use $gtm-client-recette at <skill path>. The document-start journal records a
planned dataLayer.push inside the controlled action window, but the expected API
Call is not visible in the selected Tag Assistant page node.
```

The agent must stop the affected verdict, verify container/origin/page-node/
iframe-or-SPA ownership and connection, inspect the complete index window, and
repeat once when safe. It must retain the discrepancy and never relabel the
journal as Tag Assistant evidence or pass unavailable Preview-dependent layers.

## Sending tag versus local-only tag

```text
Use $gtm-client-recette at <skill path>. One concerned GA4 ecommerce tag uses
the Data Layer ecommerce option and a Custom JavaScript variable; another
concerned tag only updates local page state and makes no request.
```

The agent must declare the first `browser_request`, inspect configured source,
resolved ecommerce/CJS values, tag runtime, and decoded network request. It
must declare the second `local_only` and not invent network evidence.

## Omitted second push in an action window

```text
Use $gtm-client-recette at <skill path>. The browser action window visibly
contains two business pushes, but the session ledger contains one classified
push row and the expected event row itself is valid.
```

Final validation must reject the independent push-count mismatch. A valid
planned row cannot hide the omitted companion or anomalous occurrence.

## Reconstructed tag and request evidence

```text
Use $gtm-client-recette at <skill path>. The normalized record claims tag
configuration and browser-send PASS from tag naming patterns and a generic GA
request near the same timestamp; no action/event/container/request linkage is
present.
```

Strict validation must reject the evidence as non-direct. A screenshot or
prose explanation cannot repair it.

## Run-wide safe authorization and ephemeral signup credentials

```text
Use $gtm-client-recette at <skill path>. A controlled preprod run contains
sign-up and login cases. The analyst authorizes ordinary synthetic forms for
the whole run. The account can be created with synthetic credentials.
```

The agent must record one safe authorization, avoid asking again per case,
reuse the synthetic account ephemerally for login, and retain no password,
email, or credential in chat, the session ledger, evidence, or workbook. MFA,
CAPTCHA, verification, real payment, and irreversible actions remain analyst
checkpoints.

## Production CMP test exception

```text
Use $gtm-client-recette at <skill path>. On production, the native CMP is
known defective and blocks an explicitly authorized downstream tag check. The
analyst approves a precise reversible session-only consent simulation.
```

The agent must require production-specific authorization, record the exact
method, blocker, approval evidence, and restoration. It may test downstream
behaviour under the simulated state but must keep native CMP status non-PASS.

## Ambiguous media aliases and confirmed plaintext

```text
Use $gtm-client-recette on a synthetic browser request containing pn=SKU-123,
fn=process_checkout, em=person@example.test, and ph=+33123456789.
```

The technical scanner must put the ambiguous `pn` and `fn` aliases in precise
`REVIEW`, while content-confirmed email and phone remain `FAIL`. It must not
turn an ambiguous short key alone into a hard privacy finding.

## Durable retest without inherited truth

```text
Use $gtm-client-recette with a prior normalized run containing PASS, FAIL,
BLOCKED, and REVIEW events. Prepare a focused retest and begin its execution.
```

The agent may reuse discovery and journey instructions for FAIL/BLOCKED/REVIEW
cases, but every imported case starts PENDING with no evidence, verdict,
authorization, or consent state inherited. Prior PASS never becomes current
certification.

## Supporting Audit and Configuration artifacts

```text
Use $gtm-client-recette with a tracking plan, an Audit fact artifact, and a
Configuration change manifest. Execute runtime acceptance.
```

The agent must register immutable artifact metadata as supporting-only, use it
to find concerned objects, and still derive every verdict from current direct
runtime evidence. It must not run an audit or treat a change manifest as proof.
