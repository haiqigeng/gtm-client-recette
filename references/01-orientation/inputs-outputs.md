# Inputs And Outputs

## Inputs

Accept the client's original tracking-plan format: XLSX, CSV, sheet export,
document, screenshot, mock-up, or analyst explanation. Also collect:

- website/environment URL;
- GTM account, web container, workspace, and preview environment when known;
- journey steps or permission to infer candidate actions;
- expected events, dataLayer paths, values, tags, variables, parameters, and
  consent behaviour;
- analyst identity, browser/device context, and execution date when available.

Do not force the client to transform the source into a fixed schema. Preserve
source sheet, row, cell, section, or screenshot references when normalizing it.

## Outputs

Produce a detailed `.xlsx` workbook with at least:

- run and environment context;
- journey coverage;
- one row per event, value, variable, tag, tag parameter, and consent check;
- separate raw API-call and resolved Data Layer evidence;
- fired and not-fired tag results;
- observed non-firing reason for every wanted tag that does not fire;
- unexpected events and tags;
- evidence catalogue with screenshots, panel captures, URLs, or machine-readable
  observations;
- status, confidence/source, and detailed notes.

The workbook is the achievement artifact. A chat explanation alone is not a
completed recette.
