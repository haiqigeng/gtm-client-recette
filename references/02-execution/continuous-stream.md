# Continuous dataLayer and Preview stream

## Gapless segments

Review from recorder installation to final closure using ordered segments:
`INITIAL_LOAD`, `ACTION`, `INTER_ACTION`, and `FINAL`. Each segment stores
exclusive start and inclusive end cursors for both Tag Assistant Preview events
and dataLayer calls. Adjacent segments share exact boundaries; gaps and overlaps
are invalid. Every settled action has exactly one matching `ACTION` segment.

## Every dataLayer call is accounted for

For every recorder call index in a segment, classify every push argument:

- `BUSINESS_EVENT`: a custom top-level `event`; map it to one business push;
- `TECHNICAL_EVENT`: a directly observed `gtm.*` lifecycle event;
- `STATE_UPDATE`: an object without a top-level event field;
- `NON_EVENT`: a non-object/function or empty call without an event field.

An argument with an event field cannot be hidden as a state update or non-event.
Incomplete/truncated captures cannot close a final segment. Use
`classify_datalayer_snapshot.py` to create the exhaustive draft; resolve every
custom event to a push before certification.

## Business-push judgement

Classify each business event as expected, companion, duplicate, premature,
delayed, wrong order, wrong context, or unplanned relevant. Every anomalous push
maps to a known event group and an `unexpected` row so it affects the event
verdict. Preserve its URL, page state, segment, Preview index, dataLayer call
index, container, reason, and direct evidence.

This includes events between two planned interactions. For example, after
`view_item_list` and before `view_item`, a mystery custom event is still
classified and reported even though neither action explicitly expected it.

## Settlement

Use adaptive quiet windows. Restart the window when a relevant business or
state call appears. If the stream never settles, absence, count, duplication,
and ordering cannot be certified; use `BLOCKED`, not an inferred pass/fail.

If recorder and Preview disagree, verify node/frame, origin, loaded container,
connection epoch, and segment boundaries, then repeat once when safe. The
recorder exposes the disagreement but cannot replace missing Preview proof.

