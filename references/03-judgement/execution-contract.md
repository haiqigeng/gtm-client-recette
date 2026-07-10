# Execution Contract

Use this lifecycle for every run:

```text
preflight plan and READY
->
orientation
-> tracking-plan recognition and analyst confirmation
-> journey and consent scope
-> dedicated browser and GTM Preview connection
-> page, Preview, consent, and event-stream readiness gate
-> website execution
-> action boundary and settled event stream
-> event-level evidence capture
-> value/tag/consent judgement
-> strict XLSX validation
```

Keep orientation, execution, and judgement distinguishable in notes and output.
An inferred journey step cannot become a confirmed expectation silently. A
browser observation cannot become a verdict without its tracking-plan rule.

Pause when authentication, consent scope or state, target environment, plan meaning, or
journey action is ambiguous. Continue only after the analyst supplies or
confirms the missing context.
