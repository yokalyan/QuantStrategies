# ORB VWAP/TWAP Filter Test

This test checks whether simple intraday VWAP/TWAP confirmation improves the TQQQ midpoint-stop ORB after applying the prior-close direction variant.

Data and shared settings:

- Data: local TQQQ one-minute file through 2025-06-02.
- Windows: fresh 2015-start and fresh 2021-start simulations.
- Direction baseline: current `opening_range` and tested `previous_close`.
- Intraday filter variants: no filter, entry VWAP side confirmation, entry TWAP side confirmation, both, and max distance from VWAP.
- Fees/slippage: not modeled.

## Filter Definitions

| Filter | Rule |
| --- | --- |
| `none` | No VWAP/TWAP filter. |
| `entry_vwap` | Long entries require entry price above session VWAP; short entries require entry price below session VWAP. |
| `entry_twap` | Long entries require entry price above session TWAP; short entries require entry price below session TWAP. |
| `entry_vwap_and_twap` | Both VWAP and TWAP side confirmation must pass. |
| `entry_vwap` + `max_vwap_distance_pct` | Side confirmation plus reject entries too far from VWAP. |

## Results

| Window | Variant | Return | CAGR | Sharpe | Max DD | Entries |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 2015-2026 | `opening_range` | 197.1% | 11.0% | 0.72 | -23.0% | 987 |
| 2015-2026 | `previous_close` | 185.6% | 10.6% | 0.76 | -18.0% | 826 |
| 2015-2026 | `previous_close` + VWAP side | 185.6% | 10.6% | 0.76 | -18.0% | 826 |
| 2015-2026 | `previous_close` + TWAP side | 185.6% | 10.6% | 0.76 | -18.0% | 826 |
| 2015-2026 | `previous_close` + VWAP/TWAP side | 185.6% | 10.6% | 0.76 | -18.0% | 826 |
| 2015-2026 | `previous_close` + VWAP side + 1% max distance | 176.9% | 10.3% | 0.75 | -17.2% | 801 |
| 2015-2026 | `previous_close` + VWAP side + 2% max distance | 189.4% | 10.7% | 0.76 | -17.5% | 824 |
| 2021-2026 | `opening_range` | 126.1% | 20.3% | 1.16 | -16.1% | 441 |
| 2021-2026 | `previous_close` | 115.6% | 19.0% | 1.16 | -8.2% | 383 |
| 2021-2026 | `previous_close` + VWAP side | 115.6% | 19.0% | 1.16 | -8.2% | 383 |
| 2021-2026 | `previous_close` + TWAP side | 115.6% | 19.0% | 1.16 | -8.2% | 383 |
| 2021-2026 | `previous_close` + VWAP/TWAP side | 115.6% | 19.0% | 1.16 | -8.2% | 383 |
| 2021-2026 | `previous_close` + VWAP side + 1% max distance | 112.0% | 18.6% | 1.15 | -9.1% | 370 |
| 2021-2026 | `previous_close` + VWAP side + 2% max distance | 117.1% | 19.2% | 1.18 | -8.2% | 382 |

## Read-Through

Basic VWAP/TWAP side confirmation adds no value here. It produces exactly the same trades as `previous_close` alone because a breakout above the opening range is already almost always above session VWAP/TWAP, and a breakdown below the opening range is already below them.

The only useful VWAP idea in this test is not confirmation, but extension control. A 2% max distance from VWAP slightly improves the 2015-start and 2021-start risk-adjusted result while preserving nearly all trades. A 1% cap is too restrictive and gives up more return without improving enough risk.

Conclusion: do not add plain VWAP/TWAP confirmation. If we continue with VWAP, study it as an overextension filter, for example `max_vwap_distance_pct: 0.02`, and validate with slippage/spreads before considering live use.
