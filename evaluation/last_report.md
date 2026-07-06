# IngreLens AI — Evaluation Report

Total cases: **20** · Overall pass rate: **100.0%**

| Metric | Value | Cases checked |
|---|---|---|
| Routing accuracy | 100.0% | 6 |
| Classification accuracy | 100.0% | 14 |
| Fallback success rate | 100.0% | 5 |
| Tool execution success | 100.0% | 20 |

## Case-by-case detail

| Dataset | Case | Result | Detail |
|---|---|---|---|
| food_label_edge_cases | fl_01_unknown_gibberish_ingredient | ✅ | kind=analysis agents_used=['classification'] |
| food_label_edge_cases | fl_02_conflicting_labels_vegan_claim_dairy_ingredient | ✅ | kind=analysis agents_used=['classification'] |
| food_label_edge_cases | fl_03_conflicting_labels_natural_flavor_ambiguous | ✅ | kind=analysis agents_used=['classification'] |
| food_label_edge_cases | fl_04_missing_ingredients_data | ✅ | kind=error agents_used=[] |
| food_label_edge_cases | fl_05_whitespace_only_ingredients | ✅ | kind=error agents_used=[] |
| food_label_edge_cases | fl_06_ocr_noisy_text_does_not_crash | ✅ | kind=analysis agents_used=['classification'] |
| food_label_edge_cases | fl_07_multi_product_comparison_healthy_vs_unhealthy | ✅ | health_score A=80 B=78 |
| allergy_cases | al_01_peanuts | ✅ | expected>=['peanuts'] found=['peanuts'] |
| allergy_cases | al_02_gluten_wheat | ✅ | expected>=['gluten'] found=['gluten', 'wheat'] |
| allergy_cases | al_03_dairy_milk | ✅ | expected>=['dairy'] found=['dairy'] |
| allergy_cases | al_04_eggs | ✅ | expected>=['eggs'] found=['dairy', 'eggs', 'gluten', 'wheat'] |
| allergy_cases | al_05_soy | ✅ | expected>=['soy'] found=['soy'] |
| allergy_cases | al_06_tree_nuts | ✅ | expected>=['tree nuts'] found=['eggs', 'tree nuts'] |
| allergy_cases | al_07_multiple_allergens_same_product | ✅ | expected>=['dairy', 'eggs', 'gluten', 'peanuts', 'soy'] found=['dairy', 'eggs', 'gluten', 'peanuts', 'soy', 'wheat'] |
| allergy_cases | al_08_no_allergens_clean_product | ✅ | expected>=[] found=[] |
| barcode_fail_cases | bc_01_all_zeros | ✅ | kind=analysis agents_used=['product_fetch', 'classification'] |
| barcode_fail_cases | bc_02_too_short | ✅ | kind=analysis agents_used=['product_fetch', 'classification'] |
| barcode_fail_cases | bc_03_non_numeric | ✅ | kind=analysis agents_used=['product_fetch', 'classification'] |
| barcode_fail_cases | bc_04_empty_string | ✅ | kind=error agents_used=[] |
| barcode_fail_cases | bc_05_real_known_product | ✅ | kind=analysis agents_used=['product_fetch', 'classification'] |
