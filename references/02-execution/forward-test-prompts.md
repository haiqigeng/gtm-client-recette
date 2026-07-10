# Forward-Test Prompts

Use raw, synthetic artifacts and a fresh agent. Do not pass the expected answer
or diagnosis.

## Test 1: Bespoke tracking plan and missing access

```text
Use the GTM Preview Recette skill at <skill path> to run a newsletter-signup
recette. The client tracking plan is an XLSX with a bespoke layout and helper
flags. A GA4 tag should fire after analytics consent. No tracking-plan file,
website URL, GTM container, or browser access is attached. Handle the request
without inventing evidence or accessing live systems.
```

Expected behaviour: request the missing inputs, keep Google sign-in manual, and
do not produce a fabricated verdict or workbook.

## Test 2: Wanted tag not fired

```text
Use the GTM Preview Recette skill at <skill path> to report these normalized
results. The wanted tag has actual status not_fired and evidence E-001, but no
non-firing reason. Build the report in strict mode.
```

Expected behaviour: strict validation fails and names the missing reason and
reason source.

## Test 3: Raw versus resolved values

```text
Use the GTM Preview Recette skill at <skill path> to evaluate this event. The
raw API-call payload contains page.type=home, while the resolved Data Layer
contains page.type=product after an earlier push. Keep both observations and
do not silently merge them.
```

Expected behaviour: create separate evidence and a review/fail decision based
on the confirmed matching rule.
