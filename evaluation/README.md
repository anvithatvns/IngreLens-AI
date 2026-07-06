# IngreLens AI — Evaluation Framework

Judge-facing proof layer: runs the real `CoordinatorAgent` and real service
classes (no mocks) against 20 hand-written edge cases across 3 datasets, and
reports 4 numbers.

## Run it

```bash
python -m evaluation.run_evaluation
# or, to also write a markdown report:
python -m evaluation.run_evaluation --report evaluation/last_report.md
```

Exit code is `0` if every case passes, `1` otherwise — safe to wire into CI.

## Datasets

| File | Cases | Covers |
|---|---|---|
| `datasets/food_label_edge_cases.json` | 7 | unknown/gibberish ingredients, conflicting labels (marketing says vegan, ingredients say otherwise), hidden animal-derived additives, missing/blank input, noisy-OCR text, multi-product health comparison |
| `datasets/allergy_cases.json` | 8 | peanuts, gluten, dairy, eggs, soy, tree nuts, multiple allergens on one product, a clean product with none |
| `datasets/barcode_fail_cases.json` | 5 | all-zero, too-short, non-numeric, empty, and one real known barcode as a sanity check |

## Metrics

| Metric | What it measures | How |
|---|---|---|
| **Routing accuracy %** | Did `CoordinatorAgent.handle()` invoke the specialist(s) the case expects (its `agents_used` audit trail), not more, not fewer? | Only counted on cases that declare `expected_agents_used`. |
| **Classification accuracy %** | Did the diet-category / allergen / health-score outcome match what the case expects? | Counted on cases with `expected_diet_category_in`, `expect_not`, `expected_allergens_include`, or the health-score comparison. |
| **Fallback success rate %** | For inputs designed to be broken (garbage barcodes, empty text), did the system degrade to a clear error or a labeled mock instead of crashing or returning nothing? | Counted on cases with `expect_fallback` / `expect_coordinator_error`. |
| **Tool execution success %** | Across every case in every dataset, did the underlying service call complete without raising? | All 20 cases. |

## Current result (last run)

100% on all 4 metrics (20/20 cases) — see `evaluation/last_report.md` for the
full case-by-case detail table. One real bug this harness caught and a fix
was applied for: whitespace-only ingredient text used to fall through to
classification instead of being treated as missing data (fixed in
`CoordinatorAgent.handle()`). One known, disclosed limitation remains — see
the Risk Checklist in the README: heavily character-corrupted OCR text can
cause the vector-search fallback to match a semantically unrelated
ingredient, which can under-classify the diet category even though the
mismatched ingredient still correctly lands in `non_vegan_ingredients`. The
`fl_06` case documents this rather than hiding it.

## Extending it

Add a case to the relevant JSON file and re-run — no code changes needed for
a new case of an existing type. A genuinely new case *type* (e.g. a new kind
of conflict) needs a matching branch in the relevant `run_*_cases()` function
in `run_evaluation.py`.
