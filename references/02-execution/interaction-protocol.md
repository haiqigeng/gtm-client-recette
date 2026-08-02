# Interaction Protocol

## First response: preflight only

When invoked for a live run, do not open GTM, read client files, inspect the
website, infer a journey, or generate output. First show no more than five short
bullets adapted to the request. Prefix every bullet with exactly one plain
responsibility label: `Analyst`, `Codex`, or `Shared`.

- `Analyst`: Provide the tracking plan or acceptance rule and target environment.
- `Codex`: After `READY`, interpret the plan and attach or open the controlled browser session.
- `Analyst`: Complete protected authentication inside that controlled session.
- `Shared`: Confirm container, workspace, Preview connection, target origin, and scope.
- `Codex`: Cover every applicable interaction in plan order, reconcile the event stream, give event verdicts, and build the XLSX.

State which analyst-approved attached or dedicated browser context will be
used. Authentication outside that controlled context does not carry over.
Never ask for, copy, store, log, or automate protected or real credentials.
Synthetic credentials created for a safe controlled test may be used
ephemerally in that same browser run, but never shown in chat or retained in
the session ledger, evidence, or workbook.

List only missing essentials: acceptance specification and target environment.
Mention supplied journeys, URLs, screenshots, GTM identifiers, and consent
scenarios as optional supporting context when relevant. Do not require them
when they can be inferred or are outside scope.

Finish with: `Reply READY to begin.`

## Commands and state

Use simple replies for checkpoints:

- `READY`: begin scope normalization.
- `CONFIRM`: accept a material interpretation or consequential action.
- `CORRECT: ...`: change the interpretation before execution continues.
- `SIGNED IN`: confirm protected authentication in the dedicated session.
- `DONE`: confirm completion of a protected website step.
- `APPROVE CMP OVERRIDE`: approve the exact temporary override just described.
- `DECLINE CMP OVERRIDE`: keep affected checks blocked and continue unaffected work.
- `PAUSE`: stop without closing or changing the session.
- `SKIP: ...`: confirm an item as out of scope with a reason.
- `REPEAT EVENT: ...`: rerun or reinspect the named event.

Do not require repeated `continue` or `generate report` replies. Proceed
automatically through analyst-independent work.

A full recette initializes run-wide authority for equivalent ordinary form
inputs, privacy acknowledgements, opt-ins that are part of the tested
conversion, safe synthetic identity, and ordinary form submission. Do not ask
again for every form or lead. Record any additional explicit scope with
`preview_session_ledger.py authorize`. Neither default nor additional authority
covers a protected checkpoint or the separate CMP-override approval.

## Progress updates

Before a new stage or analyst checkpoint, use:

```text
Current stage: <plain-language stage>
Responsible: <Analyst, Codex, or Shared>
Completed: <short evidence-based update>
Required: <one concrete action or "Nothing right now">
Next: <next execution step>
```

Pause only when a choice or action truly belongs to the analyst. Ask one concise
question when ambiguity could change a verdict or cause a consequential effect.

## Protected checkpoints

Keep Google sign-in, MFA, CAPTCHA, email/SMS verification, magic links, real
payment, external approvals, irreversible actions, and unresolved
consequential choices under analyst control.

At a protected checkpoint:

1. preserve the Preview connection and current action boundary;
2. explain the exact step the analyst must complete in the controlled session;
3. wait for `SIGNED IN` or `DONE`;
4. rediscover all browser surfaces and verify connection after handback;
5. resume the same event automatically.

Assign final `BLOCKED` only when the analyst cannot or does not complete the
step, no safe test method exists, or an evidenced external condition prevents
execution. Never skip the remainder silently.

An ordinary privacy checkbox, opt-in, or form control is not a protected
checkpoint. If it cannot be operated, retain the failed action window and try
scroll-into-view, label click, direct-control click, pointer click, keyboard
toggle, and one clean-state retry. Only then use `UI_CONTROL_BLOCKER`; do not
mislabel it as consent or missing authorization.

## Per-event feedback

After completing every applicable interaction case for a planned event,
provide one aggregate result and continue. Show one status/reason per canonical
layer, then one subrow per in-scope tag and tag-related layer. Keep excluded
detected tags visible with their scope reason:

```text
Event 07 — add_to_cart: PASS
- raw_api_call: PASS — exact API Call matched
- resolved_data_layer: PASS — value/type matched
- GA4 - add_to_cart / tag_firing: PASS — fired once
- GA4 - add_to_cart / browser request: PASS — one matching request
- Meta - AddToCart: OUT_OF_SCOPE — outside analytics-only tag scope
```

For a failure:

```text
Event 08 — begin_checkout: FAIL
- raw_api_call: FAIL — items[0].price expected number 29.90; observed string "29.90"
- GA4 - begin_checkout / tag_firing: PASS — fired once
- GA4 - begin_checkout / tag_parameter: FAIL — runtime price is string "29.90"
- GA4 - begin_checkout / browser request: PASS — one matching request
- Retest: /checkout, CTA "Commander", item=IZZI
```

For a blocker:

```text
Event 09 — purchase: BLOCKED
- Checkout reached
- Analyst intervention requested
- No approved test payment method was available
```

Do not list unrelated tags. After coverage, repeat every event once in a
concise final list in original plan order. Group homogeneous successful cases
with the tested count, but name each distinct failed, blocked, or review case
and its placement/value. Do not emit one final verdict after a representative
click while other applicable cases remain pending.

For every non-PASS event, also state the exact URL, placement, element,
interaction, and material variant needed to retest it.
