"""
Stock Analysis Dashboard (Legacy Entry Point)
=============================================

This file is deprecated. The dashboard has been refactored into a modular structure.

New location: src/app/dashboard/

Run the new dashboard with:
    streamlit run src/app/dashboard/app.py

Or use this legacy entry point which will redirect to the new dashboard.
"""

import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import and run the new modular dashboard
from src.app.dashboard import main

if __name__ == "__main__":
    main()
