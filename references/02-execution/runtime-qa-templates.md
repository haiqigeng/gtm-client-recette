# Runtime QA Templates

## Run context

```text
Plan / acceptance source:
Acceptance scope:
Tag scope / exact explicit tags:
Ordinary-journey authority / protected exclusions:
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
Event group / case ID:
Element / placement / material variant:
Discovery source / scope:
Detected tag inventory / in-scope and excluded tags:
Frozen applicability card / mandatory and conditional predicates:
Action ID:
Retry of action ID:
Attempt number:
Requirement IDs:
Page / placement / element / state:
Action value / type / source:
Supplied or inferred:
Preview connected before:
Target ready before:
Consent state before:
Last event before:
Action timestamp:
Interaction outcome:
Independent completion signal:
First event after:
Settled final event:
Quiet window / timeout:
Relevant stream settled:
Settlement reason:
Observed business-push count:
Every canonical layer result / predicate / evidence IDs:
Every in-scope tag/layer result / value/type / evidence IDs:
Action-boundary evidence ID:
```

## Business-push reconciliation

```text
Action window / event-index range:
Event index / event name:
Plan-event mapping:
Page / action / state / trigger result:
Classification: expected | companion | duplicate | premature | delayed | wrong_order | wrong_context | unplanned_relevant
Classification reason / observed push ID:
Occurrence verdict / evidence IDs:
```

## Event feedback

```text
Event <plan order> — <event name>: <status>
- Cases executed / applicable / limited:
- One row per canonical layer: status / reason / evidence:
- One subrow per in-scope tag and tag layer: status / value/type / evidence:
- Detected out-of-scope tags / reason:
- <affected placement/value and expected versus observed result>
- <destination/trigger/consent/business/privacy/client/regression result when applicable>
- Exact retest URL / placement / element / interaction / variant for non-PASS:
```

## Destination evidence

```text
Vendor / destination / owning container:
Expected vendor event / conversion name:
Expected request behaviour / endpoint:
Observed request count / request ID / method / URL:
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
Run-wide safe authorization ID / scope, if applicable:
Default ordinary-journey authority used:
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
Environment / production exception authorization if applicable:
Exact temporary method and values:
Requirements to unblock:
Not validated by this override:
Reversal/session scope:
Native CMP status / native acceptance in scope:
Approval evidence / production approval evidence:
Restoration confirmation:
```

Do not execute the override until explicit approval is recorded.
