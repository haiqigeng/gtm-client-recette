# Interaction Protocol

## First response: preflight only

When invoked for a live run, do not open GTM, read client files, inspect the
website, infer a journey, or generate output. First show no more than five short
bullets adapted to the request. Prefix every bullet with exactly one plain
responsibility label: `Analyst`, `Codex`, or `Shared`.

- `Analyst`: Provide the tracking plan or acceptance rule and target environment.
- `Codex`: After `READY`, interpret the plan and open the dedicated Playwright session.
- `Analyst`: Complete protected authentication inside that dedicated session.
- `Shared`: Confirm container, workspace, Preview connection, target origin, and scope.
- `Codex`: Execute or infer every journey in plan order, give event verdicts, and build the XLSX.

State that authentication in another browser does not authenticate the
dedicated Playwright session. Never ask for, copy, store, log, or automate
credentials.

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
2. explain the exact step the analyst must complete in the dedicated session;
3. wait for `SIGNED IN` or `DONE`;
4. rediscover all browser surfaces and verify connection after handback;
5. resume the same event automatically.

Assign final `BLOCKED` only when the analyst cannot or does not complete the
step, no safe test method exists, or an evidenced external condition prevents
execution. Never skip the remainder silently.

## Per-event feedback

After every planned event, provide one result and continue:

```text
Event 07 — add_to_cart: PASS
```

For a failure:

```text
Event 08 — begin_checkout: FAIL
- ecommerce.items[0].price: expected number 29.90; observed string "29.90"
- GA4 tag fired once with runtime price string "29.90"
```

For a blocker:

```text
Event 09 — purchase: BLOCKED
- Checkout reached
- Analyst intervention requested
- No approved test payment method was available
```

Do not list unrelated tags. After coverage, repeat every event once in a
concise final list in original plan order.
