#!/bin/bash
# =============================================================================
# Mid-term Stock Planner - Dashboard Launcher
# =============================================================================
# Usage: ./run_dashboard.sh [port]
#
# Options:
#   port    Optional port number (default: 8501)
#
# Examples:
#   ./run_dashboard.sh          # Run on default port 8501
#   ./run_dashboard.sh 8502     # Run on port 8502
# =============================================================================

set -e

# Get script directory (project root)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Port (default 8501)
PORT="${1:-8501}"

echo "=============================================="
echo "  Mid-term Stock Planner Dashboard"
echo "=============================================="
echo "Project: $SCRIPT_DIR"
echo "Port: $PORT"
echo "=============================================="

# Activate virtual environment if it exists
if [ -f "$HOME/venv/bin/activate" ]; then
    echo "Activating virtual environment..."
    source "$HOME/venv/bin/activate"
elif [ -f "venv/bin/activate" ]; then
    echo "Activating local virtual environment..."
    source venv/bin/activate
elif [ -f ".venv/bin/activate" ]; then
    echo "Activating .venv virtual environment..."
    source .venv/bin/activate
fi

# Check if streamlit is installed
if ! command -v streamlit &> /dev/null; then
    echo "Error: Streamlit not found. Please install it:"
    echo "  pip install streamlit"
    exit 1
fi

# Kill any existing Streamlit processes on this port
echo "Checking for existing processes on port $PORT..."
lsof -ti:$PORT | xargs kill -9 2>/dev/null || true

# Run the dashboard
echo ""
echo "Starting dashboard..."
echo "URL: http://localhost:$PORT"
echo ""
echo "Press Ctrl+C to stop"
echo "=============================================="

streamlit run src/app/dashboard.py --server.port "$PORT" --server.headless true
