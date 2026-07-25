# Acceptance Criteria

A full recette is complete only when:

- the plan interpretation and two ordered inventories are established;
- every in-scope event was attempted in original plan order;
- undocumented journeys were inferred and relevant alternatives explored;
- every protected checkpoint was offered to the analyst before final
  `BLOCKED`;
- GTM account, container, workspace, connected domain, target origin, and
  starting state are recorded;
- every action has readiness, boundary, and settled-stream evidence;
- every occurred event has exact raw Tag Assistant API Call and separate
  resolved Data Layer evidence;
- every applicable field, type, GTM variable, concerned tag, firing condition,
  runtime parameter, and consent condition has its own verdict;
- every wanted non-fired tag has an evidenced reason or the canonical
  reason-not-established statement;
- relevant unexpected events, duplicate pushes, and tags are recorded;
- continuous event verdicts and the final ordered event summary are delivered;
- schema-v2 strict validation passes;
- the detailed XLSX opens and passes workbook reload checks.

For a scoped recette, apply the same criteria to the declared layers and never
imply certification of excluded layers.

Any missing gate leaves the run incomplete; name the exact missing or blocked
evidence.
