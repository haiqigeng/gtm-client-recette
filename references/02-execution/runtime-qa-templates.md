# Runtime QA Templates

## Execution header

```text
QA date:
Environment:
Browser/device:
Target URL:
Consent scenario:
GTM account/container/workspace:
Preview environment:
Tag Assistant session:
Evidence locations:
Known limitations:
```

## Event row

```text
Journey:
Step:
Event order:
Event name:
API call payload:
Resolved Data Layer values:
Expected values:
Match rule:
Variables:
Tags fired:
Tags not fired:
Wanted-tag non-firing reason:
Consent state:
Evidence IDs:
Result:
Notes:
```

## Consent matrix

Run the relevant journey or event under each supplied state:

| State | Required checks |
| --- | --- |
| Before choice | Defaults are recorded; expected tags are blocked or allowed. |
| Refused | Tags and storage behaviour match the specification. |
| Analytics only | Analytics tags behave as expected; marketing tags remain blocked. |
| Marketing accepted | Dependent tags fire only after the consent update. |
| Preference change | Tags react without undocumented duplicate hits. |

Record CMP event, GTM event, tag status, consent values, timing/order, and
evidence for every transition.
