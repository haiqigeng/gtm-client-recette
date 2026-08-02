# Users And Questions

## Primary users

- Web analysts and analytics consultants.
- GTM specialists and analytics QA experts.
- Agencies and internal analytics teams using an AI agent with Playwright.

Assume expert familiarity with dataLayer, GTM variables, triggers, tags,
consent, Tag Assistant, and tracking-plan terminology.

## Questions answered

- Was every planned event attempted in original plan order?
- Was every applicable element, placement, branch, and material finite value
  tested rather than one representative interaction?
- Did the intended website action create the expected event occurrence?
- Did every business push in the controlled journey occur under the correct
  page, action, state, count, and order, without duplicates or wrong-context
  events?
- Did the exact raw `dataLayer.push` contain the required value, type, and
  structure?
- Did resolved Data Layer and GTM variables retain the correct state?
- Was the declared tag scope applied independently of plan-column completeness,
  with all detected exclusions still visible?
- Did every in-scope analytics or explicitly included media/client tag expose
  its configuration, firing/count, runtime values/types, and browser request?
- Did static configuration map to the correct runtime tag parameter?
- Did every analytics or media destination receive the correct browser request,
  ID, parameter, value, and type?
- Did trigger groups, exceptions, and setup/main/cleanup ordering behave as
  planned?
- Did four-signal consent state and full/cookieless/blocked transport match the
  accepted scenario?
- Did declared cross-field rules pass without forbidden sensitive-data
  exposure?
- Did SPA, responsive, cross-domain, iframe, cookie/linker, dataLayer,
  Custom-JavaScript, debug, and current-limit checks pass when applicable?
- Did any previously passing requirement regress?
- Why did a wanted tag not fire according to available evidence?
- Which protected or environmental blocker prevented execution?
- Were ordinary form/authentication gates completed and protected gates handed
  to the analyst instead of skipped?
- Were ordinary privacy controls and tested-conversion opt-ins completed
  without being misclassified as consent/authorization blockers?
- Which requirements are pass, fail, blocked, review, or deliberately outside
  scope?

Do not evaluate whether the tracking strategy itself is correct.
