# Simmer: DXY Regime Filter Refinement

| Iter | Correctness | Consistency | Test Coverage | Composite | Key Change |
|------|------------|-------------|---------------|-----------|------------|
| 0    | 5          | 8           | 6             | 6.3       | seed — dead config, hardcoded thresholds |
| 1    | 9          | 9           | 8             | 8.7       | config-driven thresholds + NaN guard + 3 edge case tests |

**Best:** iteration 1 (8.7/10)

## Key findings (judge board, iteration 0)
- `compute_dxy_scale()` hardcoded all thresholds while config.yaml defined them — dead config
- NaN input silently returned 1.0 (untested)
- No test for `enabled: false` code path
- No test for config-driven threshold overrides

## Fix applied (iteration 1)
- Added keyword args to `compute_dxy_scale()` matching `compute_dual_regime()` pattern
- Call site extracts values from `dxy_cfg` using `_dget` lambda (same as MRF pattern)
- Added `math.isnan()` guard returning 1.0 (graceful degradation)
- 3 new tests: NaN input, config-driven thresholds, enabled=false path
- 60 tests passing (was 57)
