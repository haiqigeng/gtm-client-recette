# Runtime QA Templates

## Run context

```text
Run type:
Plan / acceptance source:
Target environment and URL:
GTM account / container / workspace:
Preview environment and connected domain:
Natural starting consent:
Event and requirement inventory:
Evidence location:
Known limitations:
```

## Action boundary

```text
Action ID:
Requirement IDs:
Page and element:
Supplied or inferred:
Preview connected before:
Target ready before:
Consent state before:
Last event before:
Action timestamp:
First event after:
Settled final event:
Quiet window / timeout:
```

## Event feedback

```text
Event <plan order> — <event name>: <status>
- <failed layer or concise confirmation>
- <expected versus observed value/type, tag behaviour, parameter, or blocker>
```

## Protected checkpoint

```text
Checkpoint:
Journey reached:
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
