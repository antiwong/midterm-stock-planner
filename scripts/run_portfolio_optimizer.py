#!/usr/bin/env python3
"""
Run Portfolio Optimizer
=======================
Creates personalized portfolios based on user-defined parameters.

Usage:
    # Use preset profile
    python scripts/run_portfolio_optimizer.py --profile moderate
    
    # Custom parameters
    python scripts/run_portfolio_optimizer.py --profile custom \
        --risk-tolerance moderate \
        --target-return 0.15 \
        --portfolio-size 10 \
        --with-ai
"""

import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.analysis.portfolio_optimizer import main

if __name__ == "__main__":
    sys.exit(main())
