#!/usr/bin/env python3
"""
Mid-term Stock Planner - Dashboard Launcher
============================================

Usage:
    python run_dashboard.py [--port PORT]

Options:
    --port PORT    Port number (default: 8501)

Examples:
    python run_dashboard.py              # Run on default port 8501
    python run_dashboard.py --port 8502  # Run on port 8502
"""

import subprocess
import sys
import os
from pathlib import Path


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Launch the Mid-term Stock Planner Dashboard"
    )
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=8501,
        help="Port to run the dashboard on (default: 8501)"
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Don't open browser automatically"
    )
    
    args = parser.parse_args()
    
    # Get project root
    project_root = Path(__file__).parent.absolute()
    os.chdir(project_root)
    
    print("=" * 50)
    print("  Mid-term Stock Planner Dashboard")
    print("=" * 50)
    print(f"Project: {project_root}")
    print(f"Port: {args.port}")
    print("=" * 50)
    
    # Build streamlit command
    cmd = [
        sys.executable, "-m", "streamlit", "run",
        "src/app/dashboard.py",
        "--server.port", str(args.port),
    ]
    
    if args.no_browser:
        cmd.extend(["--server.headless", "true"])
    
    print(f"\nStarting dashboard...")
    print(f"URL: http://localhost:{args.port}")
    print("\nPress Ctrl+C to stop")
    print("=" * 50)
    
    try:
        subprocess.run(cmd, cwd=project_root)
    except KeyboardInterrupt:
        print("\n\nDashboard stopped.")


if __name__ == "__main__":
    main()
