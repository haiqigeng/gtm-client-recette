# Interaction Protocol

## First response: preflight only

When the skill is invoked, do not open GTM, inspect local client files, navigate
the website, infer a journey, or generate a report. First show no more than five
short, friendly bullets adapted to the actual request. Prefix each with exactly
one responsibility label: `Analyst`, `Codex`, or `Shared`.

- `Analyst`: Provide the tracking plan, target URL, journey, and consent scenario.
- `Codex`: After `READY`, open the dedicated Playwright browser window for this recette.
- `Analyst`: Complete Google sign-in, MFA, or CAPTCHA inside that dedicated window.
- `Shared`: Confirm the GTM account, container, workspace, Preview URL, and connected session.
- `Codex`: Run the agreed journeys, capture evidence, and generate the detailed XLSX report.

State explicitly that signing in through another browser window does not provide
access to the dedicated Playwright session. The analyst must authenticate in the
window opened for the recette. Never ask for, copy, store, or automate credentials.

Then list only the missing essentials: tracking plan, target URL, journey, and
consent scenario. Finish with: `Reply READY to begin.` Do not pretend that an
event name, website, or screenshot is a complete tracking plan.

## Commands and state

Use simple, explicit replies to control the run:

- `READY`: start scope confirmation.
- `CONFIRM`: accept the current interpretation, journey, environment, or step.
- `CORRECT: ...`: change the current plan before execution continues.
- `SIGNED IN`: confirm that manual Google authentication is complete.
- `DONE`: confirm completion of a manual website or consent action.
- `PAUSE`: stop without closing or changing the session.
- `SKIP: ...`: record an untested step with a reason.
- `REPEAT EVENT`: inspect the current event again or rerun the specified action.
- `GENERATE REPORT`: start workbook generation after coverage review.

Every progress update should use friendly labels:

```text
Current stage: <plain-language step>
Responsible: <Analyst, Codex, or Shared>
Completed: <short update>
Required: <one concrete action or "Nothing right now">
Next: <plain-language next step>
```

Proceed automatically through steps with no required manual action. Pause at
every checkpoint requiring a choice or action. Request one concise clarification
when a message is ambiguous.

## Human-controlled boundaries

Keep Google sign-in, MFA, CAPTCHA, payments, email/SMS confirmation, ambiguous
actions, and final interpretation of unresolved expectations under analyst
control. Authentication is complete only when it is performed in the dedicated
Playwright session. For authorised test journeys, complete ordinary forms and
account creation with inferred synthetic data, never real personal data, and
stop at an external verification or payment step. Accept only required terms,
privacy notices, and declarations for a synthetic test registration; decline or
leave unchecked all optional marketing and communication preferences. Resolve consent banners and
preference centres automatically: accept by default for a normal functional
journey, or apply each requested accepted/refused/partial/update state for
consent-gating or Advanced Consent Mode testing. Record the selected state and
resulting evidence in the workbook.
