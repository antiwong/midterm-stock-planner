#!/usr/bin/env python3
"""
Track Recommendation Performance
=================================
Update recommendation performance over time.
"""

import sys
from pathlib import Path
import argparse
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.analytics.analysis_service import AnalysisService
from src.analytics.models import get_db
from typing import Optional


def update_recommendation_performance(
    run_id: Optional[str] = None,
    days_back: int = 30
):
    """Update recommendation performance."""
    service = AnalysisService()
    db = get_db()
    session = db.get_session()
    
    try:
        from src.analytics.analysis_models import Recommendation
        
        # Get recommendations
        query = session.query(Recommendation)
        if run_id:
            query = query.filter_by(run_id=run_id)
        
        # Only update recommendations that haven't been updated recently
        cutoff_date = datetime.now() - timedelta(days=1)
        query = query.filter(
            (Recommendation.tracking_updated_at.is_(None)) |
            (Recommendation.tracking_updated_at < cutoff_date)
        )
        
        recommendations = query.all()
        
        if not recommendations:
            print("No recommendations to update.")
            return
        
        print(f"Updating {len(recommendations)} recommendations...")
        
        updated = 0
        for rec in recommendations:
            try:
                # Get current price
                ticker_obj = yf.Ticker(rec.ticker)
                hist = ticker_obj.history(period="1mo")
                
                if len(hist) == 0:
                    continue
                
                current_price = hist['Close'].iloc[-1]
                
                # Calculate return if we have recommendation date and price
                if rec.recommendation_date and rec.current_price:
                    days_held = (datetime.now() - rec.recommendation_date).days
                    if days_held > 0:
                        return_pct = (current_price - rec.current_price) / rec.current_price
                        rec.actual_return = return_pct
                        
                        # Check if hit target or stop loss
                        if rec.target_price:
                            rec.hit_target = current_price >= rec.target_price
                        if rec.stop_loss:
                            rec.hit_stop_loss = current_price <= rec.stop_loss
                
                rec.tracking_updated_at = datetime.now()
                updated += 1
                
            except Exception as e:
                print(f"Error updating {rec.ticker}: {e}")
                continue
        
        session.commit()
        print(f"✅ Updated {updated} recommendations")
        
    finally:
        session.close()


def main():
    parser = argparse.ArgumentParser(description='Track recommendation performance')
    parser.add_argument('--run-id', type=str, help='Specific run ID (optional)')
    parser.add_argument('--days-back', type=int, default=30, help='Days to look back')
    
    args = parser.parse_args()
    
    update_recommendation_performance(
        run_id=args.run_id,
        days_back=args.days_back
    )


if __name__ == '__main__':
    main()
