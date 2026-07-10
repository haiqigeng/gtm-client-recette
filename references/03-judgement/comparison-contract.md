# Comparison Contract

Create one canonical comparison row for every required tracking-plan field and
tag parameter. Do not derive the final matrix from prose notes.

Each row must contain:

- journey, step, event order, and dataLayer event;
- tracking-plan source reference and expected value/rule;
- exact raw API-call value and type;
- resolved Data Layer value and type;
- GTM variable name, value, and type when used;
- tag name, configuration field, configured value, and resolved runtime value;
- tag firing status, consent state, verdict, mismatch, and evidence IDs.

Evaluate every available link independently:

```text
tracking plan
-> raw dataLayer.push
-> resolved Data Layer
-> GTM variable
-> tag configuration/runtime value
```

For fixed values, preserve exact values and types in every column. For dynamic
values, store the confirmed matching rule. If values differ, show every value;
never replace the mismatch with a generic note.

The skill requires a tracking plan or analyst-defined acceptance specification.
Do not introduce an observation-only operating mode. Unresolved plan semantics
are `REVIEW`; absent acceptance criteria block the recette.
