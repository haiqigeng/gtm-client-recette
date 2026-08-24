# Scenario coverage

Build the decision tree just in time for the current event and any causally co-occurring
claims from the same real interaction.
The tracking plan defines accepted requirements, but it may not list every material live
value.

## Discover material dimensions

Combine:

- plan scenarios, enums, conditions and examples;
- visible controls, routes, locale options and current business state;
- source, Preview, runtime and network values observed during the run;
- known platform semantics such as ecommerce, consent, acquisition and form states.

A dimension is material when it can alter occurrence, value, JSON type, order, context,
tag choice/firing, destination, consent/privacy behavior, business coherence, or verdict.
Cosmetic variation is not a scenario.

## Coverage modes

- `EXHAUSTIVE`: every known reachable finite material branch was tested.
- `PARTITIONED`: every known distinct behavior signature was tested.
- `SAMPLED`: representatives cover a justified high-cardinality signature class.
- `SINGLETON`: exactly one real material member is known and no second member exists.
- `BLOCKED`: one or more material branches could not be acquired or classified.

Unknown population size, an unexplored visible option, or an unreachable material branch
cannot be called exhaustive.

## Finite and dependent values

Test all manageable finite values, including values absent from the plan. Expectations
remain contextual: the English route expects `en`, the French route expects `fr`; either
can pass in its own scenario, but neither is accepted everywhere. Apply that selected
scenario value to every applicable source/GTM/runtime/request comparison, so an allowed
enum cannot pass merely because the wrong allowed member appeared.

For dependent values, execute every reachable material combination, not a global
Cartesian product. Example: discover shipping methods under each materially distinct
country/address state and test each available method there. Reuse a journey prefix only
while the underlying cart, identity, locale, consent, acquisition and document state are
still valid.

## High-cardinality populations

For products, content, search terms or list members:

1. define a behavior signature from component/action path, payload shape and source,
   tag/configuration set, consent gate, destination and journey precondition;
2. select one representative for each known distinct signature; add a contrasting member
   only when a second signature is known, plus applicable boundaries and exceptions;
3. compare dynamic identity fields strictly to the chosen member's real visible/business
   state, never to one global literal;
4. record why untested members are equivalent.

Two members are equivalent only when captured context supports the same behavior
signature. Different product names or IDs alone do not require a contrast. New signatures,
anomalies, failures or conditional branches expand the sample. Do not test hundreds of
equivalent items or impose an arbitrary scenario cap.

## Live values and plan gaps

A live value omitted from the plan is both evidence and a visible plan gap. If it changes
or could change the signature, create a scenario and test it. Otherwise record it as an
observed equivalent member with an evidence reference. Unknown client-specific rules are
`REVIEW`; do not invent a universal business formula.

A failure in one scenario does not silently close remaining branches. A common objective
failure can be propagated only when the same proof obligation and cause demonstrably
apply; scenario-specific values and state still need their own evidence.

## Closure and scheduling

After each action, update only the affected event's decision tree. Compiler-known
dimensions cannot be removed by an incomplete coverage annotation. Coverage errors are
reported in the event verdict; they never prevent capture or delay the first layer
feedback. Prefer the next branch with the most new information for the least safe state
transition. Reopen an earlier event when a later observation exposes a new material
branch or cross-event anomaly.

Scenario completeness closes only when every known material branch is tested, proven
equivalent, or explicitly `BLOCKED`/`REVIEW` with an exact acquisition/retest step. It is
a verdict gate, not a pile of pre-created cases.
