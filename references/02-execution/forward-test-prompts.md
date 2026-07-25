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

## Protected signup

```text
Use $gtm-preview-recette at <skill path> to test a preprod sign-up event. The
journey permits synthetic data and reaches an email verification checkpoint.
```

The agent must complete ordinary fields, ask for analyst handoff at
verification, and resume rather than silently skip.

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

## Scoped pre-CMP investigation

```text
Use $gtm-preview-recette at <skill path> with the explicit rule: identify
developer-pushed events before the first CMP initialization event. Tag
configuration and firing are outside scope.
```

The agent must use `SCOPED_ACCEPTANCE_RECETTE`, label supplemental browser
interception, and not imply full tag certification.
