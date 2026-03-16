#!/usr/bin/env python3
"""Score sentiment articles with lexicon model.

Reads data/sentiment/news.csv, scores unscored articles, saves back.
Run after download_sentiment.py to keep scores up to date.

Usage:
    python scripts/score_sentiment.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from src.sentiment.sentiment_model import LexiconSentimentModel


def main():
    news_path = Path("data/sentiment/news.csv")
    if not news_path.exists():
        print("No news data found. Run download_sentiment.py first.")
        return 1

    news = pd.read_csv(news_path)
    print(f"Loaded {len(news)} articles")

    # Score only unscored articles
    needs_scoring = news["sentiment_score"].isna() if "sentiment_score" in news.columns else pd.Series([True] * len(news))
    n_new = needs_scoring.sum()

    if n_new == 0:
        print("All articles already scored.")
        return 0

    model = LexiconSentimentModel()

    # Score headlines
    headlines = news.loc[needs_scoring, "headline"].fillna("").tolist()
    scores = model.score_texts(headlines)
    news.loc[needs_scoring, "sentiment_score"] = scores

    # Score summaries
    summaries = news.loc[needs_scoring, "summary"].fillna("").tolist()
    summary_scores = model.score_texts(summaries)
    news.loc[needs_scoring, "summary_sentiment"] = summary_scores

    # Combined score
    news.loc[needs_scoring, "combined_sentiment"] = news.loc[needs_scoring].apply(
        lambda r: 0.6 * r["sentiment_score"] + 0.4 * r["summary_sentiment"]
        if r["summary_sentiment"] != 0 else r["sentiment_score"], axis=1
    )

    news.to_csv(news_path, index=False)
    print(f"Scored {n_new} new articles ({len(news)} total)")

    # Summary
    pos = (news["combined_sentiment"] > 0.05).sum()
    neg = (news["combined_sentiment"] < -0.05).sum()
    neu = len(news) - pos - neg
    print(f"Distribution: {pos} positive, {neu} neutral, {neg} negative")

    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
