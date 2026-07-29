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

## Build a lightweight interaction census

For each planned event, identify every applicable interaction instance before
calling its coverage complete. Include distinct:

- header, menu, footer, card, CTA, form, control, and content placements;
- visible labels, destinations, product/content identities, and page contexts;
- anonymous/authenticated, responsive, conditional, or funnel branches when
  the plan or implementation makes them materially different;
- finite input values that can change occurrence, payload, sequence, or tag
  behaviour.

Use supplied URLs and screenshots first, then inspect the live DOM, accessible
names, destinations, visible controls, and reachable states. Hidden responsive
clones are not active instances in the current viewport; test another viewport
only when that context is applicable.

Use `scripts/dom_interaction_census.js` and
[interaction-and-capture-playbook.md](interaction-and-capture-playbook.md)
when a repeated or specialized surface needs deterministic discovery. The
census proposes cases; the tracking plan determines applicability and every
accepted case still requires a real isolated browser interaction.

Test every safe, finite, practical instance. Express a repeated family as one
parameterized case with an instance list, not as many hand-written scenarios,
but give every instance its own controlled action window. A homogeneous set may
share a concise final evidence summary only after every instance was executed.
A distinct failure, payload shape, placement, or trigger condition remains
separate.

Register every instance with a stable `case_id`, event group, element,
placement, material variant, URL, discovery source, and applicable layer list.
Each attempt then references that case. A retry receives a new action ID and
retains the failed prior attempt.

Exhaust small finite value domains that can materially change the output. If a
funnel exposes product counts 1 through 9 and count affects `begin_quote`,
step-view, or lead payloads, run all nine from a reset state. For genuinely
large or combinatorial domains, use semantic partitions, boundary values, and
risk-based pairwise combinations; state the covered values and the limitation.
Never silently substitute one representative interaction for full finite
coverage.

Keep this census proportional. Do not create a Cartesian product when
dimensions do not interact, and do not turn ordinary recette into a generic
site crawl.

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
verdict or before production submission, unresolved consequential effects,
account mutation, real payment, or an irreversible effect. In a confirmed
non-production environment, complete ordinary synthetic lead, registration,
and conversion submissions by default.

## Do not manufacture negative journeys

Do not visit arbitrary pages or invent absence cases merely to see whether an
event misfires. Execute planned positive journeys and reconcile every observed
business push in their controlled page-load, navigation, and interaction
windows. This exposes duplicate, premature, delayed, wrong-order, and
wrong-context events without creating speculative tests.

Create a deliberate non-firing case only when the tracking plan or explicit
acceptance rule defines one, such as a consent block, exclusion, visibility
threshold, validation error, or success-only conversion. After an observed
anomaly, a focused reproduction is allowed to confirm its source and
repeatability.

## Conditional branches and contexts

Create explicit scenario rows for error-only, A/B, personalized,
authenticated/anonymous, visibility/scroll, and responsive branches. Record
condition, acquired branch, browser context, acquisition method, and every safe
attempt.

Test every planned branch when it can be acquired safely. Use `PENDING` only
while working, then `EXECUTED`, `BLOCKED`, or confirmed `NOT_TESTED`. `REVIEW`
is a verdict for a precise semantic ambiguity, not a substitute for an
unexecuted case.

For non-deterministic requirements, use bounded attempts derived from the plan.
Observed behaviour can pass. Judge a completed bounded attempt using the plan's
declared rule. If the plan does not define what an unobserved result means, use
`REVIEW` with the exact semantic question; if execution or evidence was
prevented, use `BLOCKED`.

## Maintain three linked inventories

Keep:

1. a source-bound requirement inventory for exact comparisons;
2. an event inventory for execution, continuous feedback, and the final ordered
   summary;
3. a session-ledger case inventory for every placement, value, context, and
   retry.

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
