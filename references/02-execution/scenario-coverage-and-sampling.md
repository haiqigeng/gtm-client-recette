# Scenario coverage and sampling

## Goal

Test every materially different behavior contract, not every URL or catalogue
member. A material difference can change the event occurrence, payload/value,
data source, tag/variable/configuration/runtime contract, consent, acquisition,
page/component, or journey precondition.

## Discovery algorithm

For each plan event:

1. Inspect supplied journeys, URLs, screenshots, and the live site.
2. List candidate interactions and material dimensions: route/template,
   component/placement, locale, responsive state, user state, product/content
   shape, quantity/value boundaries, consent, acquisition, and journey state.
3. Record why each dimension is material and its source.
4. Group candidates only when their eight-part `behavior_signature` is equal:
   action path, page/component, data source, payload contract, tag contract,
   consent context, acquisition context, and journey precondition.
5. Freeze one coverage decision and bind every in-scope case to one scenario
   class and explicit value for each material dimension before the first action.

Pass those bindings explicitly when registering the case (one
`--dimension-value DIMENSION_ID=JSON_VALUE` per material dimension). Do not let
a singleton or one-case class silently stand in for an unrecorded value.

Do not group two candidates merely because they share the same event name.
Different parameter values must all be tested when they represent a finite
semantic branch or can change the accepted output.

## Exhaustion versus sampling

- `EXHAUSTIVE`: execute every finite member when each can be materially
  different. Nine quantity rules means nine isolated cases.
- `SINGLETON`: exactly one member exists.
- `PARTITIONED`: enumerate every known behavior partition, then sample inside
  high-cardinality partitions.
- `SAMPLED`: use only for a large or open population whose members share the
  same behavior signature.
- `BLOCKED`: retain the unacquired class and blocker; it cannot pass.

For a large population such as hundreds of products, select at least:

- `ORDINARY`: the common/default member;
- `CONTRAST`: the member most different on material values while preserving the
  same behavior signature;
- `BOUNDARY`: minimum/maximum, zero/one/many, long/short, or other applicable
  limits;
- `EXCEPTION`: sale, unavailable, variant-rich, missing media, or another
  discovered special class.

Do not sample across different behavior signatures. Locale, template, consent,
or acquisition can be separate classes even when the event name is identical.

## Adaptive expansion

Reopen or revise coverage when any sample exposes a new behavior signature,
an anomaly/failure, an unseen material dimension value, or a conditional
runtime branch. Record whether coverage was expanded, the population was
exhausted, or a blocker prevented expansion. A frozen closure stores the exact
coverage revision; changing it invalidates that closure and later closures.

For every class, record a `trigger_reviews` entry for each mandatory trigger:
`NEW_BEHAVIOR_SIGNATURE`, `ANOMALY_OR_FAILURE`,
`UNSEEN_MATERIAL_DIMENSION_VALUE`, and `CONDITIONAL_RUNTIME_BRANCH`. A quiet
run still requires four explicit `NOT_TRIGGERED` judgements; observed failures,
odd pushes, new signatures, or unseen values must instead be marked detected
and expanded, exhausted, or blocked.

## Stop rule

Coverage is complete only when finite material values are represented, every
sampled class has ordinary and contrast members (plus applicable boundaries),
limitations are explicit, and every expansion trigger has been reviewed. The
goal is explainable behavioral coverage—not arbitrary case counts.
