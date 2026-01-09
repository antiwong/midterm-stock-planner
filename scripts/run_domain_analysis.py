#!/usr/bin/env python3
"""
Run Domain Analysis
===================
Runs vertical (within-sector) and horizontal (across-sector) analysis
for the latest backtest run.

Usage:
    python scripts/run_domain_analysis.py [--config config.yaml] [--output output/]
"""

import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.analysis.domain_analysis import main

if __name__ == "__main__":
    sys.exit(main())
