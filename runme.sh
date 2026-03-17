# Daily analysis for all watchlists - record signals for tracking (5:45 PM ET)
cd /Users/antiwong/Documents/code/my_code/stock_all/midterm-stock-planner && .venv/bin/python scripts/paper_trading.py run --watchlist tech_giants --local --skip-refresh >> logs/analysis_tech_giants.log 2>&1

cd /Users/antiwong/Documents/code/my_code/stock_all/midterm-stock-planner && .venv/bin/python scripts/paper_trading.py run --watchlist semiconductors --local --skip-refresh >> logs/analysis_semiconductors.log 2>&1

cd /Users/antiwong/Documents/code/my_code/stock_all/midterm-stock-planner && .venv/bin/python scripts/paper_trading.py run --watchlist precious_metals --local --skip-refresh >> logs/analysis_precious_metals.log 2>&1

# Daily sentiment: Finnhub + EODHD + score (6:00 PM ET, weekdays)
cd /Users/antiwong/Documents/code/my_code/stock_all/midterm-stock-planner && .venv/bin/python scripts/download_sentiment.py --watchlist moby_picks --days 7 >> logs/sentiment_download.log 2>&1 && .venv/bin/python -c "import os; os.environ['EODHD_API_KEY']='69b82d904d4ca0.09938126'; from src.sentiment.sources.eodhd import download_eodhd_sentiment; download_eodhd_sentiment(['NVDA','AAPL','MSFT','GOOGL','AMZN','META','TSLA','AMD','INTC','ORCL','CRM','ADBE','NFLX'])" >> logs/sentiment_download.log 2>&1 && .venv/bin/python scripts/score_sentiment.py >> logs/sentiment_download.log 2>&1
