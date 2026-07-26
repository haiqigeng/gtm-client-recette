# Runtime QA Templates

## Run context

```text
Plan / acceptance source:
Acceptance scope / applicable evidence layers:
Target environment and URL:
GTM account / client-side containers / workspaces:
Container ownership by concerned tag:
Preview surfaces / environments / connected domains:
Browser contexts / viewports / user states / variants:
Natural starting consent:
Vendor families / destinations:
Previous recette / comparison source:
Event and requirement inventory:
Interaction case census / material value coverage:
Evidence location:
Supplemental journal / network capture status:
Known limitations:
```

## Action boundary

```text
Action ID:
Case / instance ID:
Requirement IDs:
Page / placement / element / state:
Action value / type / source:
Supplied or inferred:
Preview connected before:
Target ready before:
Consent state before:
Last event before:
Action timestamp:
First event after:
Settled final event:
Quiet window / timeout:
Action-boundary evidence ID:
```

## Business-push reconciliation

```text
Action window / event-index range:
Event index / event name:
Plan-event mapping:
Page / action / state / trigger result:
Classification: expected | companion | duplicate | mistimed | wrong_context | unplanned_relevant
Occurrence verdict / evidence IDs:
```

## Event feedback

```text
Event <plan order> — <event name>: <status>
- Cases executed / applicable / limited:
- <failed layer or concise confirmation>
- <affected placement/value and expected versus observed result>
- <destination/trigger/consent/business/privacy/client/regression result when applicable>
```

## Destination evidence

```text
Vendor / destination / owning container:
Expected vendor event / conversion name:
Expected request behaviour / endpoint:
Observed request count / method / URL:
Raw request paths for destination ID / event / tested parameter:
Decoded outbound parameter / state / value / type:
Primary browser-network evidence:
Supplementary helper/UI evidence:
```

## Conditional or browser context

```text
Scenario / condition / branch:
Acquisition method and attempts:
Browser context / viewport / user state:
SPA or auto-event source:
Cross-domain / cookie / linker / iframe checks:
dataLayer / Custom JavaScript / debug / current-limit checks:
```

## Privacy and business rules

```text
Sensitive-data policy / scanned targets:
Redacted findings / status:
Declared business-rule IDs:
Deterministic results / evidence:
```

## Protected checkpoint

```text
Checkpoint:
Journey reached:
Safe preceding steps completed:
Analyst action requested:
Session preserved:
Handback result:
Final blocker, if any:
Evidence IDs:
```

## CMP override approval

```text
Natural CMP blocker:
Non-production environment:
Exact temporary method and values:
Requirements to unblock:
Not validated by this override:
Reversal/session scope:
Approval evidence:
```

Do not execute the override until explicit approval is recorded.
