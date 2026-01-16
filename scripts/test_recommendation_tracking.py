"""
Test Recommendation Tracking
============================
Creates sample recommendations from existing runs and tests tracking functionality.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from datetime import datetime, timedelta
from src.analytics.models import get_db, Run
from src.analytics.analysis_models import Recommendation
from src.analytics.recommendation_tracker import RecommendationTracker
from src.app.dashboard.data import load_run_scores


def create_sample_recommendations(run_id: str, num_recommendations: int = 10):
    """Create sample recommendations from a run's top stocks."""
    print(f"\n{'='*70}")
    print(f"CREATING SAMPLE RECOMMENDATIONS FOR RUN: {run_id[:16]}...")
    print(f"{'='*70}")
    
    # Load run scores
    scores = load_run_scores(run_id)
    if not scores:
        print(f"❌ No scores found for run {run_id}")
        return 0
    
    # Get top stocks
    sorted_scores = sorted(scores, key=lambda x: x.get('score', 0), reverse=True)
    top_stocks = sorted_scores[:num_recommendations]
    
    print(f"\n📊 Found {len(scores)} stocks, creating recommendations for top {len(top_stocks)}")
    
    # Get run details
    db = get_db()
    session = db.get_session()
    
    try:
        run = session.query(Run).filter_by(run_id=run_id).first()
        if not run:
            print(f"❌ Run {run_id} not found")
            return 0
        
        # Create recommendations
        created = 0
        recommendation_date = datetime.now() - timedelta(days=7)  # 7 days ago
        
        for i, stock in enumerate(top_stocks):
            ticker = stock.get('ticker')
            score = stock.get('score', 0)
            sector = stock.get('sector', 'Unknown')
            current_price = stock.get('price', 100.0)  # Use score price or default
            
            # Determine action based on score
            if score > 0.6:
                action = 'BUY'
                confidence = min(0.9, 0.5 + score * 0.4)
                target_price = current_price * 1.15  # 15% target
                stop_loss = current_price * 0.90  # 10% stop loss
            elif score > 0.4:
                action = 'HOLD'
                confidence = 0.6
                target_price = current_price * 1.10
                stop_loss = current_price * 0.95
            elif score > 0.2:
                action = 'AVOID'
                confidence = 0.5
                target_price = None
                stop_loss = None
            else:
                action = 'SELL'
                confidence = 0.7
                target_price = current_price * 0.90
                stop_loss = current_price * 1.10
            
            # Check if recommendation already exists
            existing = session.query(Recommendation).filter_by(
                run_id=run_id,
                ticker=ticker,
                recommendation_date=recommendation_date
            ).first()
            
            if existing:
                print(f"  ⏭️  Skipping {ticker} - recommendation already exists")
                continue
            
            # Create recommendation
            rec = Recommendation(
                run_id=run_id,
                ticker=ticker,
                action=action,
                recommendation_date=recommendation_date,
                reason=f"Score: {score:.3f}, Sector: {sector}",
                confidence=confidence,
                target_price=target_price,
                stop_loss=stop_loss,
                time_horizon='medium',
                current_price=current_price,
                score=score,
                sector=sector,
                source='test'
            )
            
            session.add(rec)
            created += 1
            print(f"  ✅ Created {action} recommendation for {ticker} (score: {score:.3f})")
        
        session.commit()
        print(f"\n✅ Created {created} recommendations")
        return created
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error creating recommendations: {e}")
        import traceback
        traceback.print_exc()
        return 0
    finally:
        session.close()


def test_tracker(run_id: str = None):
    """Test the recommendation tracker."""
    print(f"\n{'='*70}")
    print("TESTING RECOMMENDATION TRACKER")
    print(f"{'='*70}")
    
    tracker = RecommendationTracker()
    
    # Update all recommendations
    print("\n1. Updating recommendation performance...")
    summary = tracker.update_all_recommendations(
        run_id=run_id,
        days_old=1
    )
    
    print(f"\n   Total recommendations: {summary['total']}")
    print(f"   Updated: {summary['updated']}")
    print(f"   Errors: {summary['errors']}")
    if summary['updated'] > 0:
        print(f"   Average return: {summary['avg_return']*100:+.2f}%")
        print(f"   Hit target rate: {summary['hit_target_rate']*100:.1f}%")
        print(f"   Hit stop loss rate: {summary['hit_stop_loss_rate']*100:.1f}%")
    
    # Get performance summary
    print("\n2. Getting performance summary...")
    perf_summary = tracker.get_recommendation_performance_summary(
        run_id=run_id,
        min_days_old=1
    )
    
    print(f"\n   Total: {perf_summary['total']}")
    print(f"   With tracking: {perf_summary['with_tracking']}")
    if perf_summary['with_tracking'] > 0:
        print(f"   Average return: {perf_summary['avg_return']*100:+.2f}%")
        print(f"   Win rate: {perf_summary['win_rate']*100:.1f}%")
        print(f"   Hit target rate: {perf_summary['hit_target_rate']*100:.1f}%")
        print(f"   Best return: {perf_summary['best_return']*100:+.2f}%")
        print(f"   Worst return: {perf_summary['worst_return']*100:+.2f}%")
    
    # Get recommendations by performance
    print("\n3. Getting top performers...")
    top_performers = tracker.get_recommendations_by_performance(
        run_id=run_id,
        limit=5
    )
    
    if top_performers:
        print(f"\n   Top 5 performers:")
        for rec in top_performers:
            print(f"     {rec['ticker']}: {rec['actual_return']*100:+.2f}% ({rec['action']})")
    else:
        print("   No recommendations with tracking data")
    
    return summary, perf_summary


def main():
    """Main test function."""
    print("=" * 70)
    print("RECOMMENDATION TRACKING TEST")
    print("=" * 70)
    
    # Get latest run
    db = get_db()
    session = db.get_session()
    
    try:
        latest_run = session.query(Run).filter_by(status='completed').order_by(Run.created_at.desc()).first()
        
        if not latest_run:
            print("❌ No completed runs found. Please run an analysis first.")
            return
        
        run_id = latest_run.run_id
        print(f"\n📊 Using latest run: {run_id[:16]}... ({latest_run.name or 'Unnamed'})")
        
        # Check existing recommendations
        existing_recs = session.query(Recommendation).filter_by(run_id=run_id).count()
        print(f"📋 Existing recommendations: {existing_recs}")
        
        # Create sample recommendations if none exist
        if existing_recs == 0:
            print("\n⚠️  No recommendations found. Creating sample recommendations...")
            created = create_sample_recommendations(run_id, num_recommendations=10)
            if created == 0:
                print("❌ Failed to create recommendations")
                return
        else:
            print(f"\n✅ Found {existing_recs} existing recommendations")
        
        # Test tracker
        summary, perf_summary = test_tracker(run_id)
        
        # Show detailed recommendations
        print(f"\n{'='*70}")
        print("DETAILED RECOMMENDATIONS")
        print(f"{'='*70}")
        
        recommendations = session.query(Recommendation).filter_by(run_id=run_id).all()
        if recommendations:
            print(f"\n{'Ticker':<10} {'Action':<8} {'Date':<12} {'Price':<10} {'Return':<10} {'Target':<8}")
            print("-" * 70)
            for rec in recommendations[:10]:
                return_str = f"{rec.actual_return*100:+.2f}%" if rec.actual_return is not None else "N/A"
                target_str = "✅" if rec.hit_target else "❌" if rec.hit_target is False else "—"
                print(f"{rec.ticker:<10} {rec.action:<8} {rec.recommendation_date.strftime('%Y-%m-%d'):<12} "
                      f"${rec.current_price or 0:.2f}  {return_str:<10} {target_str}")
        else:
            print("No recommendations found")
        
        print(f"\n{'='*70}")
        print("✅ TEST COMPLETE")
        print(f"{'='*70}")
        print("\nNext steps:")
        print("1. Launch dashboard: streamlit run run_dashboard.py")
        print("2. Navigate to '📊 Recommendation Tracking' in Advanced Analytics")
        print("3. Select the run and view performance metrics")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()


if __name__ == "__main__":
    main()
