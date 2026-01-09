#!/bin/bash
# Setup API Keys for Midterm Stock Planner
# Run: source scripts/setup_env.sh

# Get script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Load from .env file if it exists
if [ -f "$PROJECT_ROOT/.env" ]; then
    echo "Loading API keys from .env file..."
    set -a
    source "$PROJECT_ROOT/.env"
    set +a
else
    echo "⚠️  .env file not found at $PROJECT_ROOT/.env"
    echo "   Using fallback keys..."
    
    # Fallback keys
    export NEWS_API_KEY="e36a02b7b52849a1b9b57317c87960c7"
    export GEMINI_API_KEY="AIzaSyCe03363TTIC-M9sAEUeVGYm3ARY1vIH7c"
fi

echo ""
echo "✅ API Keys loaded:"
[ -n "$NEWS_API_KEY" ] && echo "   NEWS_API_KEY: ${NEWS_API_KEY:0:8}..."
[ -n "$GEMINI_API_KEY" ] && echo "   GEMINI_API_KEY: ${GEMINI_API_KEY:0:8}..."
[ -n "$OPENAI_API_KEY" ] && echo "   OPENAI_API_KEY: ${OPENAI_API_KEY:0:12}..."
[ -n "$ALPHA_VANTAGE_API_KEY" ] && echo "   ALPHA_VANTAGE_API_KEY: ${ALPHA_VANTAGE_API_KEY:0:8}..."
