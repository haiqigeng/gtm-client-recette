# Forward-Test Prompts

Use anonymized raw artifacts and a fresh agent. Do not pass the expected
diagnosis.

## Bespoke workbook without journeys

```text
Use $gtm-preview-recette at <skill path>. The supplied XLSX has a bespoke layout,
event requirements, values, tags, and parameters, but no journey URLs or
screenshots. The target preprod URL is supplied. Prepare to execute the full
recette.
```

The agent must preserve source order, infer journeys, and not require the
analyst to rewrite the plan.

## Repeated placements and finite funnel values

```text
Use $gtm-preview-recette at <skill path>. A plan event applies to every header
and menu link. A later quote funnel accepts product counts 1 through 9, and the
count must alter begin_quote, step-view, and lead payloads.
```

The agent must census and execute every applicable link, then run all nine
count variants from isolated state. It may parameterize the work and group
homogeneous successes, but it must not use one representative click or count.

## Wrong-context and duplicate stream events

```text
Use $gtm-preview-recette at <skill path>. During planned positive journeys, a
plan event with a valid payload appears on an incompatible homepage and a
promotion event appears twice inside one load window.
```

The agent must inspect the entire business-push sequence, fail the
wrong-context and duplicate occurrence behaviour, and bind both to their
action-window evidence. It must not invent arbitrary negative pages before
making this determination.

## Protected signup

```text
Use $gtm-preview-recette at <skill path> to test a preprod sign-up event. The
journey permits synthetic data and reaches an email verification checkpoint.
```

The agent must complete ordinary fields, ask for analyst handoff at
verification, and resume rather than silently skip.

## Non-production ordinary lead submission

```text
Use $gtm-preview-recette at <skill path> to test a confirmed preprod lead
journey with an ordinary form and no CAPTCHA, MFA, verification, payment, or
unresolved downstream consequence.
```

The agent must use synthetic data and execute the final submission without
asking merely because it creates a test lead. Optional marketing choices stay
unchecked.

## Wanted tag not fired

```text
Use $gtm-preview-recette at <skill path> to report the attached schema-v2 data.
The wanted tag did not fire and the row lacks a reason source.
```

Strict validation must fail.

## Wrong runtime parameter

```text
Use $gtm-preview-recette at <skill path>. The event and raw field are correct.
The GA4 tag fires once, but the runtime value is string "29.90" instead of
number 29.90.
```

Firing must pass, parameter must fail, and overall must fail.

## Broken test CMP

```text
Use $gtm-preview-recette at <skill path>. The preprod CMP never initializes and
blocks downstream tag checks. A likely session-only consent update is available.
```

The agent must show evidence, describe the exact proposed override, and wait for
explicit approval. It must keep natural and simulated results separate.

## Bounded pre-CMP acceptance

```text
Use $gtm-preview-recette at <skill path> with the explicit rule: identify
developer-pushed events before the first CMP initialization event. Tag
configuration and firing are outside scope.
```

The agent must use the same recette workflow, declare only the applicable
requirements/layers, label supplemental browser interception, and not imply
tag certification.

## Multi-vendor destination and trigger sequence

```text
Use $gtm-preview-recette at <skill path> to validate the attached normalized
client-side fixture. One plan event drives a media tag and an analytics tag in
separate web containers. Browser-network, trigger-group, exception, and
setup/main/cleanup evidence are supplied.
```

The agent must keep atomic destination rows, container ownership, firing,
outbound parameter, trigger, and sequence verdicts separate. It must not claim
vendor ingestion.

## Sensitive data and cross-field failure

```text
Use $gtm-preview-recette at <skill path> on the attached synthetic client-side
artifact. The tracking plan declares ecommerce cross-field rules and a
sensitive-data policy.
```

The agent must run deterministic rules, redact every detected value, and reject
a false PASS. Do not tell it which field is wrong.

## Conditional mobile SPA regression

```text
Use $gtm-preview-recette at <skill path>. The prior normalized recette and a
current mobile A/B SPA fixture are supplied.
```

The agent must verify branch acquisition, viewport, navigation source,
dataLayer integrity, and requirement-level regression without running a general
container audit.

## Existing browser handoff and Preview recovery

```text
Use $gtm-preview-recette at <skill path>. The analyst has approved the attached
browser session containing signed-in GTM and Tag Assistant tabs. During the
journey, Preview disconnects after a redirect.
```

The agent must use the approved controlled session without copying credentials,
preserve the last reliable cursor, reconnect the same container/origin, and
repeat only the affected action.

## Embedded plan assets and repeated DOM family

```text
Use $gtm-preview-recette at <skill path>. The supplied XLSX contains hyperlinks,
cell comments and embedded journey screenshots. A planned footer event applies
to every visible internal footer link.
```

The agent must extract the workbook evidence, build a visible-element census,
execute every applicable link through a real isolated interaction, and preserve
source coordinates.

## Early push and unload-time media request

```text
Use $gtm-preview-recette at <skill path>. A planned event is pushed before the
page becomes interactive and its media tag sends through a navigation-time
beacon. One request body contains multiple newline-delimited records.
```

The agent must install supplemental capture before page scripts, cross-check
the exact Tag Assistant API Call, retain the navigation request, decode the
batch without equating request count with event count, and preserve the
dataLayer/tag/runtime/request verdict chain.
