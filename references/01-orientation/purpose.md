# Purpose

Run daily, expert acceptance testing for an existing client-side GTM
implementation. Treat the tracking plan or explicit analyst-defined acceptance
rule as the specification for accepted values and journey support—not as the
evidence-layer selector. Execute the necessary real website journeys, reconcile each
source-bound requirement with GTM Preview evidence, cover every applicable
interaction and material variant, and provide immediate plan-ordered event
feedback plus a validated detailed XLSX.

Cover the complete client-side acceptance surface: analytics tags by default,
explicit plan-declared media destinations or broader client-side tags on request,
multiple web containers and destinations, real signal source, browser network
requests, trigger/sequence logic, consent, declared cross-field rules,
redacted sensitive-data safeguards, conditional/browser contexts, and
previous-run regression when supplied. Server-side GTM remains out of scope.

For every planned dataLayer event, enforce the complete action/raw/resolved/
tag-inventory/variable/configuration/firing/runtime/request/sensitive chain and
report every layer plus every in-scope tag independently.

Journey execution and evidence reconciliation are inseparable. Do not optimize
for workbook production at the expense of coverage, or for journey completion
at the expense of exact evidence. Reconcile every business push in the
continuous planned journey so valid-looking events that are duplicated,
mistimed, or fired in the wrong context remain visible.
