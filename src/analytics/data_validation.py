"""
Data Validation for AI Insights
================================
Validates data quality before generating AI insights to catch issues early.
"""

from typing import Dict, List, Any, Tuple, Optional
import pandas as pd
import numpy as np
from collections import Counter


class DataValidationError(Exception):
    """Raised when data validation fails."""
    pass


class InsightsDataValidator:
    """Validates data quality before generating AI insights."""
    
    def __init__(self):
        self.warnings = []
        self.errors = []
        self.checks_passed = []
    
    def validate(self, scores_df: pd.DataFrame) -> Tuple[bool, Dict[str, Any]]:
        """
        Validate data quality for AI insights generation.
        
        Args:
            scores_df: DataFrame with stock scores and metadata
            
        Returns:
            Tuple of (is_valid, validation_report)
        """
        self.warnings = []
        self.errors = []
        self.checks_passed = []
        
        # Basic data checks
        self._check_data_completeness(scores_df)
        self._check_score_distribution(scores_df)
        self._check_sector_scores(scores_df)
        self._check_score_ranges(scores_df)
        self._check_missing_critical_fields(scores_df)
        self._check_data_diversity(scores_df)
        
        # Build report
        report = {
            'is_valid': len(self.errors) == 0,
            'has_warnings': len(self.warnings) > 0,
            'errors': self.errors,
            'warnings': self.warnings,
            'checks_passed': self.checks_passed,
            'summary': self._generate_summary()
        }
        
        return report['is_valid'], report
    
    def _check_data_completeness(self, scores_df: pd.DataFrame):
        """Check if required data is present."""
        if scores_df.empty:
            self.errors.append("No stock data available")
            return
        
        self.checks_passed.append("Data completeness: ✓")
        
        # Check for required columns
        required_cols = ['ticker', 'score']
        missing_cols = [col for col in required_cols if col not in scores_df.columns]
        if missing_cols:
            self.errors.append(f"Missing required columns: {', '.join(missing_cols)}")
        else:
            self.checks_passed.append("Required columns present: ✓")
        
        # Check for empty scores
        null_scores = scores_df['score'].isna().sum()
        if null_scores > 0:
            self.warnings.append(f"{null_scores} stocks have null scores")
        
        # Check minimum data points
        if len(scores_df) < 10:
            self.warnings.append(f"Only {len(scores_df)} stocks available (recommended: 20+)")
    
    def _check_score_distribution(self, scores_df: pd.DataFrame):
        """Check if scores are properly distributed."""
        if 'score' not in scores_df.columns:
            return
        
        scores = scores_df['score'].dropna()
        if len(scores) == 0:
            self.errors.append("No valid scores found")
            return
        
        # Check for all identical scores
        unique_scores = scores.nunique()
        if unique_scores == 1:
            self.errors.append(
                f"All {len(scores)} stocks have identical scores ({scores.iloc[0]:.4f}). "
                "This indicates a data normalization issue."
            )
            return
        
        self.checks_passed.append(f"Score distribution: {unique_scores} unique values ✓")
        
        # Check score variance
        score_std = scores.std()
        if score_std < 0.001:
            self.errors.append(
                f"Score variance is extremely low (std={score_std:.6f}). "
                "Scores are not differentiated enough for meaningful analysis."
            )
        elif score_std < 0.01:
            self.warnings.append(
                f"Low score variance (std={score_std:.4f}). "
                "Scores may not be sufficiently differentiated."
            )
        else:
            self.checks_passed.append(f"Score variance: std={score_std:.4f} ✓")
        
        # Check score range
        score_range = scores.max() - scores.min()
        if score_range < 0.01:
            self.warnings.append(
                f"Very narrow score range ({score_range:.4f}). "
                "Limited differentiation between stocks."
            )
    
    def _check_sector_scores(self, scores_df: pd.DataFrame):
        """Check if sector scores are properly differentiated."""
        if 'sector' not in scores_df.columns or 'score' not in scores_df.columns:
            self.warnings.append("Sector information not available for validation")
            return
        
        # Calculate average score per sector
        sector_avg_scores = scores_df.groupby('sector')['score'].mean()
        
        # Check if all sector averages are identical
        unique_sector_avgs = sector_avg_scores.nunique()
        if unique_sector_avgs == 1:
            avg_value = sector_avg_scores.iloc[0]
            self.errors.append(
                f"All {len(sector_avg_scores)} sectors have identical average scores ({avg_value:.4f}). "
                "This indicates a data normalization or calculation issue. "
                "Sector analysis will not be meaningful."
            )
            return
        
        self.checks_passed.append(f"Sector differentiation: {unique_sector_avgs} unique sector averages ✓")
        
        # Check sector score variance
        sector_std = sector_avg_scores.std()
        if sector_std < 0.001:
            self.errors.append(
                f"Sector score variance is extremely low (std={sector_std:.6f}). "
                "Sectors are not differentiated enough for meaningful analysis."
            )
        elif sector_std < 0.01:
            self.warnings.append(
                f"Low sector score variance (std={sector_std:.4f}). "
                "Sector analysis may not be meaningful."
            )
        
        # Check for sectors with too few stocks
        sector_counts = scores_df['sector'].value_counts()
        small_sectors = sector_counts[sector_counts < 3]
        if len(small_sectors) > 0:
            self.warnings.append(
                f"{len(small_sectors)} sectors have fewer than 3 stocks: {', '.join(small_sectors.index[:5])}"
            )
    
    def _check_score_ranges(self, scores_df: pd.DataFrame):
        """Check if scores are in expected ranges."""
        if 'score' not in scores_df.columns:
            return
        
        scores = scores_df['score'].dropna()
        if len(scores) == 0:
            return
        
        # Check for extreme values
        if scores.min() < -10 or scores.max() > 10:
            self.warnings.append(
                f"Scores outside typical range: min={scores.min():.2f}, max={scores.max():.2f}"
            )
        
        # Check for scores clustered at boundaries
        boundary_count = ((scores == scores.min()) | (scores == scores.max())).sum()
        if boundary_count > len(scores) * 0.1:  # More than 10% at boundaries
            self.warnings.append(
                f"{boundary_count} stocks ({boundary_count/len(scores)*100:.1f}%) have boundary scores. "
                "Possible clipping or normalization issue."
            )
    
    def _check_missing_critical_fields(self, scores_df: pd.DataFrame):
        """Check for missing critical fields that affect insight quality."""
        critical_fields = {
            'sector': 'Sector information',
            'tech_score': 'Technical scores',
            'fund_score': 'Fundamental scores',
            'sent_score': 'Sentiment scores',
            'rsi': 'RSI indicators',
            'return_21d': '21-day returns'
        }
        
        missing_fields = []
        for field, description in critical_fields.items():
            if field not in scores_df.columns:
                missing_fields.append(description)
        
        if missing_fields:
            self.warnings.append(
                f"Missing fields that enhance insights: {', '.join(missing_fields)}"
            )
        else:
            self.checks_passed.append("Critical fields present: ✓")
    
    def _check_data_diversity(self, scores_df: pd.DataFrame):
        """Check if data has sufficient diversity for meaningful insights."""
        # Check sector diversity
        if 'sector' in scores_df.columns:
            unique_sectors = scores_df['sector'].nunique()
            if unique_sectors < 3:
                self.warnings.append(
                    f"Only {unique_sectors} sectors represented. Limited sector diversity."
                )
            else:
                self.checks_passed.append(f"Sector diversity: {unique_sectors} sectors ✓")
        
        # Check for excessive concentration
        if 'score' in scores_df.columns:
            top_10_pct = scores_df.nlargest(max(1, len(scores_df) // 10), 'score')
            top_10_avg = top_10_pct['score'].mean()
            bottom_10_avg = scores_df.nsmallest(max(1, len(scores_df) // 10), 'score')['score'].mean()
            
            if abs(top_10_avg - bottom_10_avg) < 0.01:
                self.warnings.append(
                    "Top and bottom 10% of stocks have very similar scores. "
                    "Limited differentiation for recommendations."
                )
    
    def _generate_summary(self) -> str:
        """Generate a human-readable summary of validation results."""
        if len(self.errors) > 0:
            return (
                f"❌ Validation FAILED: {len(self.errors)} error(s) found. "
                "AI insights generation is NOT recommended until issues are resolved."
            )
        elif len(self.warnings) > 0:
            return (
                f"⚠️ Validation PASSED with {len(self.warnings)} warning(s). "
                "AI insights may be generated but quality may be reduced."
            )
        else:
            return (
                f"✅ Validation PASSED: All {len(self.checks_passed)} checks passed. "
                "Data quality is good for AI insights generation."
            )
    
    def get_validation_message(self, report: Dict[str, Any]) -> str:
        """Get formatted validation message for display."""
        lines = [report['summary'], ""]
        
        if self.errors:
            lines.append("**Errors (must fix):**")
            for i, error in enumerate(self.errors, 1):
                lines.append(f"{i}. {error}")
            lines.append("")
        
        if self.warnings:
            lines.append("**Warnings (recommended to fix):**")
            for i, warning in enumerate(self.warnings, 1):
                lines.append(f"{i}. {warning}")
            lines.append("")
        
        if self.checks_passed:
            lines.append("**Checks Passed:**")
            for check in self.checks_passed[:5]:  # Show first 5
                lines.append(f"  • {check}")
            if len(self.checks_passed) > 5:
                lines.append(f"  ... and {len(self.checks_passed) - 5} more")
        
        return "\n".join(lines)
