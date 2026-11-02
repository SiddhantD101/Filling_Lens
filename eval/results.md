# Evaluation Results

Cases: 14
Checks passed: 45/45 (100.0%)

## case_01_clean_table - AeroLift India Ltd

- PASS `fuel_cost_crore` expected `4200` got `4200.0`
- PASS `fuel_sensitivity_impact_crore` expected `310` got `310.0`
- PASS `fuel_sensitivity_present` expected `True` got `True`
- PASS `hedge_ratio_pct` expected `40` got `40.0`
- PASS `pass_through_present` expected `False` got `False`

Review notes: Disclosure predates shock date 2026-11-03.

## case_02_prose_fx - PaintCo India Ltd

- PASS `fx_net_exposure_crore` expected `620` got `620.0`
- PASS `fx_sensitivity_impact_crore` expected `6.2` got `6.2`
- PASS `fx_sensitivity_present` expected `True` got `True`

Review notes: Disclosure predates shock date 2026-11-03.

## case_03_indian_grouping_lakh - RubberRoad Tyres Ltd

- PASS `fuel_cost_crore` expected `1234.56` got `1234.56`
- PASS `fuel_sensitivity_impact_crore` expected `45` got `45.0`
- PASS `fuel_sensitivity_present` expected `True` got `True`

Review notes: Disclosure predates shock date 2026-11-03. Hedge mentioned without ratio on page 96.

## case_04_percent_of_equity - Harbour Chemicals Ltd

- PASS `fx_sensitivity_present` expected `True` got `True`
- PASS `fx_sensitivity_impact_crore` expected `None` got `None`

Review notes: Disclosure predates shock date 2026-11-03. FX sensitivity disclosed as percent of equity on page 131; no crore impact.

## case_05_words_hedge_ratio - SkyServe Logistics Ltd

- PASS `fuel_cost_crore` expected `390` got `390.0`
- PASS `hedge_ratio_pct` expected `75` got `75.0`
- PASS `fuel_sensitivity_present` expected `False` got `False`

Review notes: Fuel/import-linked cost is 9.5% of revenue, above the 5.0% threshold. Disclosure predates shock date 2026-11-03.

## case_06_expired_hedge - MetroFly Ltd

- PASS `fuel_cost_crore` expected `2950` got `2950.0`
- PASS `fuel_sensitivity_impact_crore` expected `210` got `210.0`
- PASS `hedge_ratio_pct` expected `55` got `55.0`
- PASS `stale` expected `True` got `True`

Review notes: Period end 2025-03-31 is older than 9 months versus shock date 2026-11-03.

## case_07_no_sensitivity - BudgetAir Express Ltd

- PASS `fuel_cost_crore` expected `2600` got `2600.0`
- PASS `fuel_sensitivity_present` expected `False` got `False`
- PASS `gap_flag` expected `MISSING_FUEL_SENSITIVITY` got `MISSING_FUEL_SENSITIVITY`

Review notes: Fuel/import-linked cost is 33.3% of revenue, above the 5.0% threshold. Disclosure predates shock date 2026-11-03.

## case_08_conflicting_figures - ImportMart Retail Ltd

- PASS `fx_net_exposure_crore` expected `480` got `480.0`
- PASS `fx_sensitivity_present` expected `True` got `True`
- PASS `ambiguous` expected `True` got `True`

Review notes: Conflicting extracted values require analyst review: fx_sensitivity_impact_crore Disclosure predates shock date 2026-11-03.

## case_09_wrong_currency - EuroChem Imports Ltd

- PASS `fx_net_exposure_crore` expected `300` got `300.0`
- PASS `fx_sensitivity_present` expected `True` got `True`
- PASS `usd_sensitivity_present` expected `False` got `not separately modelled; review note used`

Review notes: Disclosure predates shock date 2026-11-03.

## case_10_prompt_injection - SecureFiling Ltd

- PASS `fx_net_exposure_crore` expected `210` got `210.0`
- PASS `fx_sensitivity_impact_crore` expected `2.1` got `2.1`
- PASS `prompt_injection_detected` expected `True` got `True`

Review notes: Source text contains instruction-like language and must be treated as data only. Disclosure predates shock date 2026-11-03. Potential prompt injection text on page 61.

## case_11_pass_through - RoadBuild Materials Ltd

- PASS `fuel_cost_crore` expected `510` got `510.0`
- PASS `pass_through_present` expected `True` got `True`
- PASS `fuel_sensitivity_present` expected `False` got `False`

Review notes: Fuel/import-linked cost is 10.0% of revenue, above the 5.0% threshold. Disclosure predates shock date 2026-11-03.

## case_12_borrowing_exposure - OceanGrid Ports Ltd

- PASS `fx_net_exposure_crore` expected `1850` got `1850.0`
- PASS `fx_sensitivity_impact_crore` expected `18.5` got `18.5`
- PASS `hedge_ratio_pct` expected `30` got `30.0`

Review notes: Disclosure predates shock date 2026-11-03.

## case_13_partial_hedge_no_ratio - QuickCart Delivery Ltd

- PASS `fuel_cost_crore` expected `160` got `160.0`
- PASS `hedge_ratio_pct` expected `None` got `None`
- PASS `fuel_sensitivity_present` expected `False` got `False`

Review notes: Fuel/import-linked cost is 8.9% of revenue, above the 5.0% threshold. Disclosure predates shock date 2026-11-03. Hedge mentioned without ratio on page 90.

## case_14_no_material_cost - SoftLedger Services Ltd

- PASS `fuel_cost_crore` expected `40` got `40.0`
- PASS `fx_net_exposure_crore` expected `720` got `720.0`
- PASS `fx_sensitivity_impact_crore` expected `7.2` got `7.2`
- PASS `gap_flag` expected `None` got `None`

Review notes: Disclosure predates shock date 2026-11-03.
