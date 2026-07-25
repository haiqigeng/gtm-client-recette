# Journey Inference And Coverage

## Resolve the route

Use this authority order:

1. supplied journey or test scenario;
2. screenshot, mock-up, or implementation specification;
3. analyst instruction;
4. tracking-plan URL, selector, label, or action;
5. website exploration inferred from event semantics and visible elements.

Translate a production example path to the confirmed test origin before
discarding it. Preserve the original and translated URLs in the ledger.

When no route is supplied, rank candidate actions using:

- event name and parameter semantics;
- visible labels and accessible names;
- navigation menus and page content;
- relevant CTAs, cards, forms, and authenticated entry points;
- internal search and sitemap links;
- preceding and following events in plan order.

Mark the selected action as inferred, record its inference source and
confidence, and continue automatically when the action is ordinary and
reversible.

## Explore before classifying

Before declaring an element unavailable, attempt relevant alternatives:

- direct tracking-plan or mock-up URL;
- test-origin translation of production paths;
- header, footer, and contextual navigation;
- internal search;
- visible CTA and equivalent responsive element;
- authenticated versus anonymous entry point;
- alternate branch required by the planned value or tag outcome.

Record every attempted route, selector, visible label, and outcome. Stop
exploring when all plan requirements are covered; do not crawl unrelated site
features.

Ask the analyst when multiple plausible actions could materially change the
verdict or before payment, real lead submission, account mutation, or an
irreversible effect.

## Maintain two inventories

Keep:

1. a source-bound requirement inventory for exact comparisons;
2. an event inventory for execution, continuous feedback, and the final ordered
   summary.

Do not let runtime Preview order replace tracking-plan order. Record both.

After each event, update its requirements and coverage state. Before reporting,
compare normalized results against both inventories. Attempt relevant
alternatives for every pending in-scope event.

Use:

- `EXECUTED` when the planned action and evidence capture ran;
- `BLOCKED` after an attempted action met an evidenced blocker;
- `REVIEW` for unresolved plan meaning or ambiguous evidence;
- `NOT_TESTED` only for explicitly confirmed out-of-scope work.

Never classify HTTP 403, disconnected Preview, CAPTCHA, unavailable payment,
or another demonstrated blocker as `NOT_TESTED`.
