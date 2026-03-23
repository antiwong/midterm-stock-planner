"""
SentimentPulse Trigger Layer.

Operates AFTER the cross-sectional ranker. Receives the ranked candidate list
and gates entry timing using sentiment features from SentimentPulse CSVs.

NEVER feed these features into the ranker itself.
Sentiment features degrade cross-sectional ranking (Sharpe -0.18 to -0.28).
See docs/10-improvement-suggestions.md for root cause analysis.

Gap 5: Includes NO_DATA signal to distinguish missing data from neutral sentiment.
"""

import logging
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class TriggerSignal(str, Enum):
    BUY = "BUY"                  # Sentiment confirms ranker — enter
    BUY_STRONG = "BUY_STRONG"   # Contrarian divergence — enter with higher conviction
    HOLD = "HOLD"                # Sentiment neutral — wait for alignment
    HOLD_BEARISH = "HOLD_BEARISH"  # Sentiment conflicts — skip this window
    WAIT_EVENT = "WAIT_EVENT"    # Forward event detected — wait for resolution
    NO_DATA = "NO_DATA"          # Gap 5: No SentimentPulse coverage for this ticker


@dataclass
class TriggerResult:
    ticker: str
    signal: TriggerSignal
    confidence: float
    composite_score: float
    options_signal: float
    trends_spike: bool
    regime: str
    forward_event: Optional[str] = None
    days_to_event: Optional[int] = None
    reasoning: str = ""


# Columns that must NEVER appear in feature data (Gap 2: look-ahead prevention)
FORBIDDEN_COLS = {
    'actual_return_5d', 'actual_return_10d', 'actual_return_20d',
    'signal_correct_5d', 'signal_correct_10d', 'signal_correct_20d',
}


class SentimentTrigger:
    """Evaluate entry timing for ranker-selected candidates."""

    def __init__(self, config: dict, sentiment_dir: str):
        self.config = config
        self.sentiment_dir = Path(sentiment_dir)
        self.thresholds = config.get('sentiment_trigger', {})

    def load_latest_sentiment(self, ticker: str,
                               lookback_days: int = 30) -> pd.DataFrame:
        """Load most recent sentiment rows for a ticker from DuckDB."""
        try:
            from src.sentiment.sentiment_adapter import load_sentimentpulse_for_trigger
            df = load_sentimentpulse_for_trigger(ticker, lookback_days=lookback_days)
            if not df.empty:
                # Gap 2: Hard assertion — no feedback columns allowed
                contamination = FORBIDDEN_COLS & set(df.columns)
                if contamination:
                    raise ValueError(
                        f"Look-ahead contamination for {ticker}: {contamination}"
                    )
                return df.sort_values('date')
            return pd.DataFrame()
        except Exception as e:
            logger.warning("Failed to load sentiment for %s: %s", ticker, e)
            return pd.DataFrame()

    def evaluate(self, ticker: str, ranker_rank: int,
                 watchlist: str) -> TriggerResult:
        """Evaluate whether to enter a position on a ranker-selected candidate."""
        df = self.load_latest_sentiment(ticker, lookback_days=30)

        # Gap 5: Distinguish NO_DATA from neutral
        if df.empty:
            return TriggerResult(
                ticker=ticker, signal=TriggerSignal.NO_DATA,
                confidence=0.0, composite_score=0.0,
                options_signal=0.0, trends_spike=False,
                regime='NOISE', forward_event=None, days_to_event=None,
                reasoning="No SentimentPulse data available for this ticker"
            )

        # Check if composite_score has non-null values
        has_composite = (
            'composite_score' in df.columns
            and df['composite_score'].notna().any()
        )
        if not has_composite:
            return TriggerResult(
                ticker=ticker, signal=TriggerSignal.NO_DATA,
                confidence=0.0, composite_score=0.0,
                options_signal=0.0, trends_spike=False,
                regime='NOISE', forward_event=None, days_to_event=None,
                reasoning="SentimentPulse data exists but composite_score is all null"
            )

        if len(df) < 3:
            return TriggerResult(
                ticker=ticker, signal=TriggerSignal.HOLD,
                confidence=0.0, composite_score=0.0,
                options_signal=0.0, trends_spike=False,
                regime='NOISE', forward_event=None, days_to_event=None,
                reasoning="Insufficient history — fewer than 3 days of data"
            )

        features = self._build_features(df, watchlist)
        return self._evaluate_signal(ticker, features)

    def _build_features(self, df: pd.DataFrame, watchlist: str) -> Dict:
        """Compute trigger features from historical sentiment data."""
        decay = self.thresholds.get('decay_halflife_by_category', {})
        wl_cfg = self.thresholds.get('watchlist_overrides', {}).get(watchlist, {})

        df = df.sort_values('date').copy()
        df['days_ago'] = (pd.Timestamp.today() - pd.to_datetime(df['date'])).dt.days

        # EMA scores
        ema_spans = wl_cfg.get('ema_spans', self.thresholds.get('ema_spans', [3, 7]))
        scores = df.set_index('date')['composite_score'].dropna()

        if len(scores) < 2:
            ema_short = scores.iloc[-1] if len(scores) > 0 else 0.0
            ema_long = ema_short
        else:
            ema_short = float(scores.ewm(span=ema_spans[0]).mean().iloc[-1])
            ema_long = float(scores.ewm(span=ema_spans[1]).mean().iloc[-1])

        sentiment_momentum = ema_short - ema_long
        latest = df.iloc[-1]

        def _bool(v, default=False):
            """Safe bool conversion handling pandas NA."""
            try:
                if pd.isna(v):
                    return default
                return bool(v)
            except (TypeError, ValueError):
                return default

        def _float(v, default=0.0):
            """Safe float conversion handling pandas NA."""
            try:
                if pd.isna(v):
                    return default
                return float(v)
            except (TypeError, ValueError):
                return default

        def _int(v, default=0):
            try:
                if pd.isna(v):
                    return default
                return int(v)
            except (TypeError, ValueError):
                return default

        def _str(v, default=''):
            try:
                if pd.isna(v):
                    return default
                return str(v)
            except (TypeError, ValueError):
                return default

        return {
            'data_sufficient': True,
            'composite_latest': _float(latest.get('composite_score', 0) or 0),
            'ema_short': ema_short,
            'ema_long': ema_long,
            'sentiment_momentum': sentiment_momentum,
            'buzz_ratio': _float(latest.get('buzz_ratio', 1.0) or 1.0),
            'buzz_zscore': _float(latest.get('buzz_zscore', 0.0) or 0.0),
            'source_agreement': _float(latest.get('source_agreement', 0.2) or 0.2),
            'conviction_asymmetry': _float(latest.get('conviction_asymmetry', 0.0) or 0.0),
            'options_signal': _float(latest.get('options_sentiment_signal', 0.0) or 0.0),
            'options_pcr': _float(latest.get('options_pcr', 1.0) or 1.0),
            'iv_percentile': _float(latest.get('iv_percentile', 50.0) or 50.0),
            'unusual_options_flag': _bool(latest.get('unusual_options_flag', False)),
            'unusual_options_direction': _str(latest.get('unusual_options_direction', 'neutral')),
            'trends_spike': _bool(latest.get('trends_spike_flag', False)),
            'divergence': _bool(latest.get('price_divergence', False)),
            'divergence_direction': _str(latest.get('divergence_direction', 'none')),
            'regime': _str(latest.get('sentiment_regime', 'NOISE')),
            'forward_event_detected': _bool(latest.get('forward_event_detected', False)),
            'forward_event_type': latest.get('forward_event_type'),
            'days_to_event': latest.get('days_to_event'),
            'insider_cluster_flag': _bool(latest.get('insider_cluster_flag', False)),
            'insider_signal': _float(latest.get('insider_signal', 0.0) or 0.0),
            'insider_net_30d': _float(latest.get('insider_net_30d', 0.0) or 0.0),
            'insider_buy_count_30d': _int(latest.get('insider_buy_count_30d', 0) or 0),
            'propagation_flag': _bool(latest.get('propagation_flag', False)),
            'has_primary_source': _bool(latest.get('has_primary_source', False)),
            'organic_score': _float(latest.get('organic_score', 0.0) or 0.0),
            'headline_count': _int(latest.get('headline_count', 0) or 0),
            'options_data_available': _bool(latest.get('options_data_available', False)),
            'analyst_action_detected': _bool(latest.get('analyst_action_detected', False)),
            'analyst_firm': _str(latest.get('analyst_firm', '') or ''),
            'analyst_action_type': _str(latest.get('analyst_action_type', '') or ''),
            'earnings_days_to': latest.get('earnings_days_to'),
            'earnings_season_flag': _str(latest.get('earnings_season_flag', '') or ''),
            'forward_event_date': _str(latest.get('forward_event_date', '') or ''),
        }

    def _evaluate_signal(self, ticker: str, f: Dict) -> TriggerResult:
        """Apply trigger logic to computed features."""
        cfg = self.thresholds
        threshold = cfg.get('entry_confirmation_threshold', 0.20)
        options_veto_pcr = cfg.get('options_veto_pcr', 1.8)
        options_veto_iv = cfg.get('options_veto_iv_pct', 85)

        score = f['composite_latest']
        ema = f['ema_short']
        reasons = []

        # GATE: Block propagated signals without organic corroboration
        if f.get('propagation_flag') and not f.get('has_primary_source'):
            organic_count = f.get('headline_count', 0)
            if organic_count < 2:
                reasons.append("Propagated signal — insufficient organic corroboration")
                return TriggerResult(
                    ticker=ticker, signal=TriggerSignal.HOLD,
                    confidence=0.3, composite_score=score,
                    options_signal=f['options_signal'], trends_spike=f['trends_spike'],
                    regime=f['regime'], forward_event=f.get('forward_event_type'),
                    days_to_event=f.get('days_to_event'),
                    reasoning=" | ".join(reasons),
                )

        # FLAG: Earnings proximity — add to reasons
        earnings_days = f.get('earnings_days_to')
        if earnings_days is not None and 0 < earnings_days <= 7:
            reasons.append(f"Earnings in {int(earnings_days)}d — elevated uncertainty")

        # FLAG: Analyst action
        if f.get('analyst_action_detected') and f.get('analyst_firm'):
            reasons.append(f"Analyst: {f['analyst_firm']} {f.get('analyst_action_type', '')}")

        # Options veto
        veto = (
            f.get('options_data_available', False)
            and f['options_pcr'] > options_veto_pcr
            and f['iv_percentile'] > options_veto_iv
            and f['options_signal'] < -0.3
        )
        bullish_override = (
            cfg.get('unusual_options_override', True)
            and f['unusual_options_flag']
            and f['unusual_options_direction'] == 'bullish'
        )

        if veto and not bullish_override:
            reasons.append(f"OPTIONS VETO: P/C={f['options_pcr']:.2f}, IV%={f['iv_percentile']:.0f}")
            return TriggerResult(
                ticker=ticker, signal=TriggerSignal.HOLD_BEARISH,
                confidence=0.8, composite_score=score,
                options_signal=f['options_signal'], trends_spike=f['trends_spike'],
                regime=f['regime'], forward_event=f.get('forward_event_type'),
                days_to_event=f.get('days_to_event'),
                reasoning=" | ".join(reasons),
            )

        # Wait for forward event
        dte = f.get('days_to_event')
        if f['forward_event_detected'] and dte is not None and 1 <= dte <= 5:
            reasons.append(f"WAIT: {f.get('forward_event_type')} in {dte} days")
            return TriggerResult(
                ticker=ticker, signal=TriggerSignal.WAIT_EVENT,
                confidence=0.7, composite_score=score,
                options_signal=f['options_signal'], trends_spike=f['trends_spike'],
                regime=f['regime'], forward_event=f.get('forward_event_type'),
                days_to_event=dte,
                reasoning=" | ".join(reasons),
            )

        # Contrarian
        if f['divergence'] and f['regime'] == 'CONTRARIAN':
            conf = 0.75
            if bullish_override and f['divergence_direction'] == 'bullish_on_falling':
                conf = 0.90
                reasons.append("Unusual bullish flow confirms contrarian")
            if f['trends_spike']:
                conf = min(conf + 0.05, 0.95)
            reasons.insert(0, f"CONTRARIAN: {f['divergence_direction']}, score={score:.3f}")
            return TriggerResult(
                ticker=ticker, signal=TriggerSignal.BUY_STRONG,
                confidence=conf, composite_score=score,
                options_signal=f['options_signal'], trends_spike=f['trends_spike'],
                regime=f['regime'], forward_event=f.get('forward_event_type'),
                days_to_event=f.get('days_to_event'),
                reasoning=" | ".join(reasons),
            )

        # Positive confirmation
        if score >= threshold and ema >= threshold * 0.8:
            conf = 0.60
            if f['sentiment_momentum'] > 0:
                conf += 0.08
            if f['buzz_zscore'] > 1.5:
                conf += 0.05
            if bullish_override:
                conf += 0.10
            if f['trends_spike']:
                conf += 0.05
            if f['options_signal'] > 0.1:
                conf += 0.07
            # Source agreement: high agreement = reliable signal (boost)
            # source_agreement is std dev of source scores — lower = more agreement
            if f['source_agreement'] < 0.15:
                conf += 0.05
            elif f['source_agreement'] > 0.30:
                conf -= 0.10
                reasons.append(f"Source disagreement (std={f['source_agreement']:.2f})")
            # Gap 8: Insider cluster buy upgrade
            if f.get('insider_cluster_flag'):
                conf += 0.10
                reasons.append("Insider cluster buy (3+ insiders in 7d window)")
            if f['regime'] == 'NOISE':
                conf -= 0.15
            if f['propagation_flag']:
                conf -= 0.10
            conf = min(max(conf, 0.0), 1.0)
            reasons.insert(0, f"BUY: score={score:.3f}, ema={ema:.3f}")
            return TriggerResult(
                ticker=ticker, signal=TriggerSignal.BUY,
                confidence=conf, composite_score=score,
                options_signal=f['options_signal'], trends_spike=f['trends_spike'],
                regime=f['regime'], forward_event=f.get('forward_event_type'),
                days_to_event=f.get('days_to_event'),
                reasoning=" | ".join(reasons),
            )

        # MODIFIER: Conviction asymmetry — upgrade HOLD to BUY
        conviction_asym = f.get('conviction_asymmetry', 0)
        if conviction_asym and conviction_asym > 0.4 and score > 0.10:
            reasons.append(f"Conviction asymmetry {conviction_asym:.2f} — bullish evidence dominant")
            conf = 0.55
            if f.get('insider_cluster_flag'):
                conf += 0.10
            return TriggerResult(
                ticker=ticker, signal=TriggerSignal.BUY,
                confidence=min(conf, 1.0), composite_score=score,
                options_signal=f['options_signal'], trends_spike=f['trends_spike'],
                regime=f['regime'], forward_event=f.get('forward_event_type'),
                days_to_event=f.get('days_to_event'),
                reasoning=" | ".join(reasons),
            )

        # MODIFIER: Insider cluster buy upgrade from HOLD
        if f.get('insider_cluster_flag') and score > 0.10:
            reasons.append(f"Insider cluster buy ({f.get('insider_buy_count_30d', '?')} buyers, "
                           f"net ${f.get('insider_net_30d', 0):,.0f})")
            return TriggerResult(
                ticker=ticker, signal=TriggerSignal.BUY,
                confidence=0.55, composite_score=score,
                options_signal=f['options_signal'], trends_spike=f['trends_spike'],
                regime=f['regime'], forward_event=f.get('forward_event_type'),
                days_to_event=f.get('days_to_event'),
                reasoning=" | ".join(reasons),
            )

        # Default: HOLD
        reasons.append(f"HOLD: score={score:.3f} < threshold={threshold}")
        return TriggerResult(
            ticker=ticker, signal=TriggerSignal.HOLD,
            confidence=0.5, composite_score=score,
            options_signal=f['options_signal'], trends_spike=f['trends_spike'],
            regime=f['regime'], forward_event=f.get('forward_event_type'),
            days_to_event=f.get('days_to_event'),
            reasoning=" | ".join(reasons),
        )
