# Acceptance Criteria

A recette is complete only when:

- the client tracking-plan interpretation is confirmed or explicitly analyst-
  provided;
- the journey and consent scenarios are defined and their inferred steps are
  marked;
- GTM account, container, workspace, Preview connection, target URL, and
  initial consent state are recorded;
- every planned event is covered by a status;
- every tested event has separate API-call and Data Layer evidence;
- every relevant variable, tag, tag parameter, consent expectation, and
  unexpected item has a row-level result;
- every wanted-but-not-fired tag has a direct or explicitly inferred reason;
- every result row links to evidence;
- the detailed XLSX exists, opens, and passes strict validation.

Any missing gate is `Incomplete / blocked`, with the missing evidence named.
