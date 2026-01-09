#!/usr/bin/env python3
"""Verify database has feature values."""
import sqlite3

conn = sqlite3.connect('data/analysis.db')
cursor = conn.cursor()

# Get latest run
cursor.execute("SELECT run_id, name FROM runs ORDER BY created_at DESC LIMIT 1")
run = cursor.fetchone()
print(f"Latest run: {run[0]} - {run[1]}")
print()

# Get scores with all columns
cursor.execute("""
    SELECT ticker, score, rank, percentile, predicted_return, rsi, return_21d, return_63d, volatility
    FROM stock_scores 
    WHERE run_id = ?
    ORDER BY rank
    LIMIT 10
""", (run[0],))

rows = cursor.fetchall()
print(f"{'Ticker':<8} {'Score':>8} {'Rank':>5} {'Pctl':>6} {'PredRet':>8} {'RSI':>6} {'Ret21d':>8} {'Ret63d':>8} {'Vol':>8}")
print("-" * 80)
for row in rows:
    ticker, score, rank, pctl, pred, rsi, r21, r63, vol = row
    print(f"{ticker:<8} {score or 0:>8.4f} {rank or 0:>5} {pctl or 0:>6.1f} {pred or 0:>8.4f} {rsi or 0:>6.1f} {r21 or 0:>8.4f} {r63 or 0:>8.4f} {vol or 0:>8.4f}")

conn.close()
