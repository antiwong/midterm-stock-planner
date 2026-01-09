#!/bin/bash
# Reset Dashboard Script
# Clears all runs, database, cache, and prepares for fresh start

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

echo "🧹 Resetting Dashboard..."
echo ""

# 1. Remove all run folders
echo "1. Removing all run folders..."
find output -type d -name "run_*" -exec rm -rf {} + 2>/dev/null || true
echo "   ✅ Run folders cleared"

# 2. Remove database
echo "2. Removing database..."
rm -f data/analysis.db
echo "   ✅ Database removed"

# 3. Clear Python cache
echo "3. Clearing Python cache..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true
echo "   ✅ Python cache cleared"

# 4. Clear Streamlit cache (if exists)
echo "4. Clearing Streamlit cache..."
rm -rf .streamlit/cache 2>/dev/null || true
rm -rf ~/.streamlit/cache 2>/dev/null || true
echo "   ✅ Streamlit cache cleared"

echo ""
echo "✅ Dashboard reset complete!"
echo ""
echo "📋 Next steps:"
echo "   1. Stop the Streamlit dashboard if it's running (Ctrl+C)"
echo "   2. Restart with: streamlit run src/app/dashboard/app.py"
echo "   3. The dashboard will automatically clear its cache on startup"
echo ""
