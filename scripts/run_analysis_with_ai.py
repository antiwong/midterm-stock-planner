#!/usr/bin/env python3
"""
Run Stock Analysis with AI-Powered Insights
============================================
This script runs a comprehensive stock analysis and generates
reports with AI-powered explanations and recommendations.
"""

import os
import sys
import argparse
from datetime import datetime
from pathlib import Path
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load API keys
from src.config.api_keys import load_api_keys
load_api_keys()

from src.analytics import (
    RunManager,
    ReportGenerator,
    AIInsightsGenerator,
)
from src.data.loader import DataLoader
from src.features.engineer import FeatureEngineer
from src.models.trainer import ModelTrainer
from src.sentiment.analyzer import SentimentAnalyzer
from src.config.loader import ConfigLoader


def run_analysis(
    watchlist: str = "default",
    model_type: str = "lightgbm",
    include_sentiment: bool = True,
    include_fundamentals: bool = True,
    generate_html: bool = True,
    verbose: bool = True,
):
    """
    Run a full analysis with AI insights.
    
    Args:
        watchlist: Name of watchlist to analyze
        model_type: Model type (lightgbm, ridge, ensemble)
        include_sentiment: Include sentiment analysis
        include_fundamentals: Include fundamental data
        generate_html: Generate HTML report
        verbose: Print progress
    """
    print("=" * 60)
    print("🚀 Stock Analysis with AI-Powered Insights")
    print("=" * 60)
    print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"📋 Watchlist: {watchlist}")
    print(f"🤖 Model: {model_type}")
    print(f"💬 Sentiment: {'✅' if include_sentiment else '❌'}")
    print(f"📊 Fundamentals: {'✅' if include_fundamentals else '❌'}")
    print()
    
    # Initialize components
    config = ConfigLoader().load_config()
    run_manager = RunManager()
    
    # Create run
    run_id = run_manager.create_run(
        name=f"AI Analysis - {watchlist}",
        run_type="analysis",
        config={
            "watchlist": watchlist,
            "model_type": model_type,
            "include_sentiment": include_sentiment,
            "include_fundamentals": include_fundamentals,
        }
    )
    
    if verbose:
        print(f"📝 Run ID: {run_id}")
    
    try:
        # 1. Load data
        if verbose:
            print("\n📥 Loading data...")
        
        loader = DataLoader()
        tickers = loader.load_watchlist(watchlist)
        prices = loader.load_prices(tickers)
        
        if verbose:
            print(f"   Loaded {len(tickers)} tickers, {len(prices)} price records")
        
        # 2. Feature engineering
        if verbose:
            print("\n🔧 Engineering features...")
        
        engineer = FeatureEngineer()
        features = engineer.create_features(
            prices,
            include_fundamentals=include_fundamentals,
        )
        
        if verbose:
            print(f"   Created {len(features.columns)} features")
        
        # 3. Sentiment analysis
        sentiment_scores = {}
        if include_sentiment:
            if verbose:
                print("\n💬 Analyzing sentiment...")
            
            analyzer = SentimentAnalyzer()
            for ticker in tickers[:20]:  # Limit for API rate limits
                try:
                    score = analyzer.analyze(ticker)
                    sentiment_scores[ticker] = score
                except Exception as e:
                    if verbose:
                        print(f"   ⚠️ {ticker}: {e}")
            
            if verbose:
                print(f"   Analyzed {len(sentiment_scores)} tickers")
        
        # 4. Model training & scoring
        if verbose:
            print("\n🤖 Training model and generating scores...")
        
        trainer = ModelTrainer(model_type=model_type)
        model_results = trainer.train_and_score(features, sentiment_scores)
        
        # 5. Save scores to database
        if verbose:
            print("\n💾 Saving results to database...")
        
        scores = model_results.get('scores', {})
        for rank, (ticker, score_data) in enumerate(
            sorted(scores.items(), key=lambda x: x[1].get('score', 0), reverse=True),
            1
        ):
            run_manager.add_stock_score(
                run_id=run_id,
                ticker=ticker,
                score=score_data.get('score', 0),
                rank=rank,
                tech_score=score_data.get('tech_score'),
                fund_score=score_data.get('fund_score'),
                sent_score=score_data.get('sent_score'),
                rsi=score_data.get('rsi'),
                sector=score_data.get('sector'),
                features=score_data,
            )
        
        # Update run metrics
        run_manager.update_run(
            run_id=run_id,
            status="completed",
            spearman_corr=model_results.get('spearman_corr'),
            hit_rate=model_results.get('hit_rate'),
            sharpe_ratio=model_results.get('sharpe_ratio'),
            total_return=model_results.get('total_return'),
            universe_count=len(scores),
        )
        
        # 6. Generate reports with AI insights
        if verbose:
            print("\n📝 Generating reports with AI insights...")
        
        report_gen = ReportGenerator(enable_ai_insights=True)
        output_dir = Path(f"output/{run_id}")
        
        reports = report_gen.generate_report(
            run_id=run_id,
            output_dir=output_dir,
            format="all",
            include_ai_insights=True,
        )
        
        if verbose:
            print(f"   Generated reports:")
            for fmt, path in reports.items():
                print(f"   - {fmt}: {path}")
        
        # Summary
        print("\n" + "=" * 60)
        print("✅ Analysis Complete!")
        print("=" * 60)
        print(f"📊 Stocks analyzed: {len(scores)}")
        print(f"🏆 Top pick: {list(scores.keys())[0] if scores else 'N/A'}")
        print(f"📁 Output: {output_dir}")
        print(f"🌐 HTML Report: {reports.get('html', 'N/A')}")
        print()
        
        return run_id, reports
        
    except Exception as e:
        run_manager.update_run(run_id=run_id, status="failed")
        print(f"\n❌ Error: {e}")
        raise


def main():
    parser = argparse.ArgumentParser(
        description="Run stock analysis with AI-powered insights"
    )
    parser.add_argument(
        "--watchlist", "-w",
        default="default",
        help="Watchlist to analyze (default: 'default')"
    )
    parser.add_argument(
        "--model", "-m",
        default="lightgbm",
        choices=["lightgbm", "ridge", "ensemble"],
        help="Model type to use"
    )
    parser.add_argument(
        "--no-sentiment",
        action="store_true",
        help="Skip sentiment analysis"
    )
    parser.add_argument(
        "--no-fundamentals",
        action="store_true",
        help="Skip fundamental data"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress verbose output"
    )
    
    args = parser.parse_args()
    
    run_analysis(
        watchlist=args.watchlist,
        model_type=args.model,
        include_sentiment=not args.no_sentiment,
        include_fundamentals=not args.no_fundamentals,
        verbose=not args.quiet,
    )


if __name__ == "__main__":
    main()
