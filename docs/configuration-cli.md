# Configuration & CLI

> **Part of**: [Mid-term Stock Planner Design](design.md)
> 
> This document covers configuration management, CLI commands, and run tracking.

## Related Documents

- [design.md](design.md) - Main overview and architecture
- [backtesting.md](backtesting.md) - Backtest configuration
- [model-training.md](model-training.md) - Model configuration

---

## 1. Configuration Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CONFIGURATION ARCHITECTURE                                │
└─────────────────────────────────────────────────────────────────────────────┘

                    ┌─────────────────────┐
                    │    config.yaml      │
                    │   (User Settings)   │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   Config Loader     │◄──── Environment Variables
                    │   (config.py)       │       (overrides)
                    └──────────┬──────────┘
                               │
         ┌─────────────────────┼─────────────────────┐
         │                     │                     │
         ▼                     ▼                     ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   DataConfig    │ │  FeatureConfig  │ │   ModelConfig   │
├─────────────────┤ ├─────────────────┤ ├─────────────────┤
│ • price_path    │ │ • horizon_days  │ │ • type          │
│ • fund_path     │ │ • use_extended  │ │ • target_col    │
│ • bench_path    │ │ • lookbacks     │ │ • params        │
│ • universe      │ │                 │ │                 │
└─────────────────┘ └─────────────────┘ └─────────────────┘
         │                     │                     │
         ▼                     ▼                     ▼
┌─────────────────┐ ┌─────────────────┐
│ BacktestConfig  │ │   CLIConfig     │
├─────────────────┤ ├─────────────────┤
│ • train_years   │ │ • output_format │
│ • test_months   │ │ • verbosity     │
│ • rebalance_freq│ │                 │
│ • costs_bps     │ │                 │
│ • max_weight    │ │                 │
└─────────────────┘ └─────────────────┘
```

---

## 2. Configuration Dataclasses

### 2.1 DataConfig

```python
@dataclass
class DataConfig:
    """Configuration for data loading."""
    price_path: str = "data/prices.csv"
    fundamental_path: str = "data/fundamentals.csv"
    benchmark_path: str = "data/benchmark.csv"
    universe_path: Optional[str] = "data/universe.txt"
    universe: Optional[List[str]] = None
```

### 2.2 FeatureConfig

```python
@dataclass
class FeatureConfig:
    """Configuration for feature engineering."""
    horizon_days: int = 63  # 3 months
    use_extended_indicators: bool = False
    return_lookbacks: List[int] = field(default_factory=lambda: [21, 63, 126, 252])
    vol_short_window: int = 20
    vol_long_window: int = 60
    volume_lookback: int = 20
```

### 2.3 ModelConfig

```python
@dataclass
class ModelConfig:
    """Configuration for model training."""
    type: str = "lightgbm"
    target_col: str = "target"
    test_size: float = 0.2
    random_state: int = 42
    params: Dict[str, Any] = field(default_factory=lambda: {
        "n_estimators": 300,
        "learning_rate": 0.05,
        "num_leaves": 31,
        "max_depth": -1,
        "min_child_samples": 20,
        "reg_alpha": 0.1,
        "reg_lambda": 0.1,
    })
```

### 2.4 BacktestConfig

```python
@dataclass
class BacktestConfig:
    """Configuration for backtesting."""
    train_years: int = 5
    test_months: int = 12
    step_months: int = 12
    rebalance_frequency: str = "M"
    top_n: int = 10
    max_weight: float = 0.05
    max_sector_weight: float = 0.25
    commission_bps: float = 5.0
    slippage_bps: float = 3.0
    max_turnover: float = 0.30
```

### 2.5 CLIConfig

```python
@dataclass
class CLIConfig:
    """Configuration for CLI output."""
    output_format: str = "csv"  # csv, json, table
    verbosity: str = "info"  # debug, info, warning, error
    save_models: bool = True
    save_charts: bool = True
```

---

## 3. YAML Configuration File

```yaml
# config/config.yaml

data:
  price_path: "data/prices.csv"
  fundamental_path: "data/fundamentals.csv"
  benchmark_path: "data/benchmark.csv"
  universe: ["AAPL", "MSFT", "NVDA", "AMD", "GOOGL", "META", "AMZN"]

features:
  horizon_days: 63
  use_extended_indicators: true
  return_lookbacks: [21, 63, 126, 252]
  vol_short_window: 20
  vol_long_window: 60

model:
  type: "lightgbm"
  target_col: "target"
  test_size: 0.2
  random_state: 42
  params:
    n_estimators: 300
    learning_rate: 0.05
    num_leaves: 31
    max_depth: -1
    min_child_samples: 20
    reg_alpha: 0.1
    reg_lambda: 0.1

backtest:
  train_years: 5
  test_months: 12
  rebalance_frequency: "M"
  top_n: 10
  max_weight: 0.05
  max_sector_weight: 0.25
  commission_bps: 5
  slippage_bps: 3
  max_turnover: 0.30

cli:
  output_format: "csv"
  verbosity: "info"
  save_models: true
  save_charts: true
```

---

## 4. Config Loader

```python
# src/config/config.py

def load_config(config_path: Path) -> Dict[str, Any]:
    """
    Load configuration from YAML file.
    
    Applies environment variable overrides:
    - MSP_DATA_PRICE_PATH -> data.price_path
    - MSP_MODEL_N_ESTIMATORS -> model.params.n_estimators
    - etc.
    """
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    # Apply environment variable overrides
    config = apply_env_overrides(config)
    
    return config

def apply_env_overrides(config: Dict) -> Dict:
    """Apply environment variable overrides to config."""
    env_mappings = {
        "MSP_DATA_PRICE_PATH": ["data", "price_path"],
        "MSP_DATA_FUNDAMENTAL_PATH": ["data", "fundamental_path"],
        "MSP_MODEL_N_ESTIMATORS": ["model", "params", "n_estimators"],
        # ... more mappings
    }
    
    for env_var, path in env_mappings.items():
        if env_var in os.environ:
            set_nested(config, path, os.environ[env_var])
    
    return config
```

---

## 5. CLI Commands

### 5.1 Command Structure

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CLI COMMANDS                                       │
└─────────────────────────────────────────────────────────────────────────────┘

python -m src.app.cli <command> [options]

Commands:
  run-backtest    Run walk-forward backtest
  score-latest    Score current universe
  compare-runs    Compare multiple backtest runs
  show-config     Display current configuration
```

### 5.2 run-backtest

**Troubleshooting**: If you encounter "No predictions generated" errors, use the diagnostic script:

```bash
python scripts/diagnose_backtest_data.py
```

This will check:
- Data date ranges and span
- Window size requirements vs available data
- Training dataset creation
- Date filter issues

See [backtesting.md](backtesting.md#8-troubleshooting-backtest-errors) for detailed troubleshooting guide.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  $ python -m src.app.cli run-backtest --config config.yaml                   │
└─────────────────────────────────────────────────────────────────────────────┘

Options:
  --config PATH         Path to configuration YAML file (required)
  --output-dir PATH     Output directory for results (default: runs/)
  --start-date DATE     Backtest start date (optional)
  --end-date DATE       Backtest end date (optional)
  --dry-run             Validate config without running

Flow:
  1. Load configuration
  2. Prepare training data
  3. Run walk-forward backtest
  4. Save results to runs/{timestamp}/
     ├── config.yaml
     ├── summary.json
     ├── equity_curve.csv
     ├── holdings.csv
     └── metrics.csv
```

### 5.3 score-latest

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  $ python -m src.app.cli score-latest --model models/v1 --date 2024-01-15   │
└─────────────────────────────────────────────────────────────────────────────┘

Options:
  --config PATH         Path to configuration YAML file
  --model PATH          Path to trained model directory (required)
  --date DATE           Date to score (default: latest available)
  --universe PATH       Path to universe file (optional override)
  --output PATH         Output file path (default: stdout)
  --format FORMAT       Output format: csv, json, table (default: table)
  --explanations        Include SHAP explanations

Output:
  ┌────────────────────────────────────────────────────────────────────────┐
  │  Rank  Ticker  Score   Top Factors                                     │
  │  ────────────────────────────────────────────────────────────────────  │
  │    1   NVDA    0.12    momentum (+0.06), vol (+0.02)                   │
  │    2   AMD     0.09    momentum (+0.04), growth (+0.02)                │
  │    3   AAPL    0.07    value (+0.04), quality (+0.02)                  │
  └────────────────────────────────────────────────────────────────────────┘
```

### 5.4 transfer-report (Transfer & Robustness Testing)

Runs backtest on primary and transfer universes with the same config (zero-shot). Outputs side-by-side metrics.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  $ python scripts/transfer_report.py --watchlist nasdaq_100 \               │
│        --transfer-watchlist sp500 --output output/transfer.json              │
└─────────────────────────────────────────────────────────────────────────────┘

Options:
  --config PATH           Config file (default: config/config.yaml)
  --watchlist NAME        Primary watchlist (default: universe.txt)
  --transfer-watchlist NAME  Transfer watchlist (required)
  --output PATH           JSON output for comparison
```

### 5.5 compare-runs

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  $ python -m src.app.cli compare-runs runs/run1 runs/run2 runs/run3         │
└─────────────────────────────────────────────────────────────────────────────┘

Options:
  run_dirs              Paths to run directories to compare
  --metric METRIC       Primary metric for comparison (default: sharpe)
  --output PATH         Output file for comparison report

Output:
  ┌────────────────────────────────────────────────────────────────────────┐
  │  Metric          run1        run2        run3                          │
  │  ─────────────────────────────────────────────────────────────────────│
  │  Sharpe          1.15        1.32*       1.08                          │
  │  Max DD          -12%        -10%*       -15%                          │
  │  Ann. Return     +14%        +16%*       +12%                          │
  │  * = best                                                              │
  └────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Run Tracking

### 6.1 Directory Structure

```
runs/
│
├── 2024-01-15_10-30-00/           ◄── Timestamp-based run ID
│   ├── config.yaml                ◄── Full config snapshot
│   ├── summary.json               ◄── Key metrics summary
│   ├── equity_curve.csv           ◄── Daily portfolio values
│   ├── holdings.csv               ◄── Per-period holdings
│   ├── metrics.csv                ◄── Detailed metrics
│   ├── models/                    ◄── Trained models per window
│   │   ├── window_1/
│   │   │   ├── model.txt
│   │   │   └── metadata.json
│   │   └── window_2/
│   └── charts/                    ◄── Generated charts
│       ├── equity_curve.png
│       └── drawdown.png
│
├── 2024-01-20_14-45-00/
│   └── ...
│
└── 2024-02-01_09-00-00/
    └── ...
```

### 6.2 Summary JSON

```json
{
  "run_id": "2024-01-15_10-30-00",
  "config_hash": "abc123",
  "git_commit": "def456",
  "start_time": "2024-01-15T10:30:00",
  "end_time": "2024-01-15T10:35:42",
  "metrics": {
    "total_return": 0.452,
    "annualized_return": 0.151,
    "sharpe_ratio": 1.25,
    "sortino_ratio": 1.85,
    "max_drawdown": -0.12,
    "win_rate": 0.583,
    "avg_turnover": 0.28
  },
  "windows": 4,
  "total_trades": 156
}
```

---

## 7. CLI Implementation

```python
# src/app/cli.py

import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(
        description="Mid-term Stock Planner CLI"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # run-backtest
    bt_parser = subparsers.add_parser("run-backtest")
    bt_parser.add_argument("--config", type=Path, required=True)
    bt_parser.add_argument("--output-dir", type=Path, default="runs")
    bt_parser.add_argument("--start-date", type=str)
    bt_parser.add_argument("--end-date", type=str)
    bt_parser.add_argument("--dry-run", action="store_true")
    
    # score-latest
    score_parser = subparsers.add_parser("score-latest")
    score_parser.add_argument("--config", type=Path)
    score_parser.add_argument("--model", type=Path, required=True)
    score_parser.add_argument("--date", type=str)
    score_parser.add_argument("--output", type=Path)
    score_parser.add_argument("--format", choices=["csv", "json", "table"])
    score_parser.add_argument("--explanations", action="store_true")
    
    # compare-runs
    compare_parser = subparsers.add_parser("compare-runs")
    compare_parser.add_argument("run_dirs", nargs="+", type=Path)
    compare_parser.add_argument("--metric", default="sharpe")
    compare_parser.add_argument("--output", type=Path)
    
    args = parser.parse_args()
    
    if args.command == "run-backtest":
        run_backtest_command(args)
    elif args.command == "score-latest":
        score_latest_command(args)
    elif args.command == "compare-runs":
        compare_runs_command(args)

if __name__ == "__main__":
    main()
```

---

## 8. Usage Examples

### 8.1 Run Backtest

```bash
# Basic backtest
python -m src.app.cli run-backtest --config config/config.yaml

# With date range
python -m src.app.cli run-backtest \
    --config config/config.yaml \
    --start-date 2020-01-01 \
    --end-date 2023-12-31

# Dry run to validate config
python -m src.app.cli run-backtest --config config/config.yaml --dry-run
```

### 8.2 Score Latest

```bash
# Score with explanations
python -m src.app.cli score-latest \
    --model models/20240101_v1 \
    --date 2024-01-15 \
    --explanations

# Output to CSV
python -m src.app.cli score-latest \
    --model models/20240101_v1 \
    --output scores.csv \
    --format csv
```

### 8.3 Compare Runs

```bash
python -m src.app.cli compare-runs \
    runs/2024-01-15_10-30-00 \
    runs/2024-01-20_14-45-00 \
    --metric sharpe
```

---

## Related Documents

- **Back to**: [design.md](design.md) - Main overview
- **Backtest Config**: [backtesting.md](backtesting.md) - Backtest settings
- **Model Config**: [model-training.md](model-training.md) - Model settings
