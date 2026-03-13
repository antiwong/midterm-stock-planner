"""Feature registry for regression testing.

Central definition of all available features, their groups, dependencies,
tunable parameters, and column mappings. Used by the orchestrator to
selectively compute features for each regression step.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class FeatureGroup(Enum):
    RETURNS = "returns"
    VOLATILITY = "volatility"
    VOLUME = "volume"
    VALUATION = "valuation"
    GAP = "gap"
    TECHNICAL = "technical"
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    SENTIMENT = "sentiment"


@dataclass
class TunableParam:
    """Specification for a tunable parameter."""
    type: str  # "int" or "float"
    min_val: float
    max_val: float
    default: float
    prior: str = "uniform"  # "uniform" or "log-uniform"


@dataclass
class FeatureSpec:
    """Specification for a single feature or feature sub-group."""
    name: str
    columns: List[str]
    group: FeatureGroup
    depends_on: List[str] = field(default_factory=list)
    tunable_params: Dict[str, TunableParam] = field(default_factory=dict)
    enabled_by_default: bool = True
    description: str = ""


@dataclass
class FeatureSet:
    """A named set of features for a regression run."""
    name: str
    feature_specs: List[str]  # FeatureSpec names
    description: str = ""

    def get_columns(self, registry: "FeatureRegistry") -> List[str]:
        """Resolve to actual column names."""
        cols = []
        for spec_name in self.feature_specs:
            spec = registry.get(spec_name)
            if spec:
                cols.extend(spec.columns)
        return cols


# Default feature addition order for regression testing
DEFAULT_FEATURE_ORDER = [
    "valuation",
    "rsi",
    "macd",
    "bollinger",
    "atr",
    "adx",
    "obv",
    "gap",
    "momentum",
    "mean_reversion",
    "sentiment",
]

# Default baseline features (minimal viable model)
DEFAULT_BASELINE = ["returns", "volatility", "volume"]


class FeatureRegistry:
    """Central registry of all available features."""

    def __init__(self):
        self._specs: Dict[str, FeatureSpec] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        """Register all known features from the codebase."""
        # --- Returns group ---
        self.register(FeatureSpec(
            name="returns",
            columns=["return_1m", "return_3m", "return_6m", "return_12m"],
            group=FeatureGroup.RETURNS,
            description="Multi-period returns (1m, 3m, 6m, 12m)",
        ))

        # --- Volatility group ---
        self.register(FeatureSpec(
            name="volatility",
            columns=["vol_20d", "vol_60d"],
            group=FeatureGroup.VOLATILITY,
            description="Rolling standard deviation of returns",
        ))

        # --- Volume group ---
        self.register(FeatureSpec(
            name="volume",
            columns=["dollar_volume_20d", "volume_ratio", "turnover_20d"],
            group=FeatureGroup.VOLUME,
            description="Dollar volume, volume ratio, turnover",
        ))

        # --- Valuation group ---
        self.register(FeatureSpec(
            name="valuation",
            columns=["pe_ratio", "pb_ratio", "earnings_yield"],
            group=FeatureGroup.VALUATION,
            description="Fundamental valuation ratios",
        ))

        # --- Gap features (QuantaAlpha-inspired) ---
        self.register(FeatureSpec(
            name="gap",
            columns=[
                "overnight_gap_pct", "gap_vs_true_range",
                "gap_acceptance_score_20d", "gap_acceptance_vol_weighted_20d",
            ],
            group=FeatureGroup.GAP,
            tunable_params={
                "gap_vs_tr_lookback": TunableParam("int", 5, 20, 10),
                "acceptance_window": TunableParam("int", 10, 40, 20),
            },
            description="Overnight gap features (QuantaAlpha-inspired)",
        ))

        # --- Technical indicators (individual) ---
        self.register(FeatureSpec(
            name="rsi",
            columns=["rsi"],
            group=FeatureGroup.TECHNICAL,
            tunable_params={
                "rsi_period": TunableParam("int", 7, 28, 14),
            },
            description="Relative Strength Index",
        ))

        self.register(FeatureSpec(
            name="macd",
            columns=["macd", "macd_signal", "macd_histogram"],
            group=FeatureGroup.TECHNICAL,
            tunable_params={
                "macd_fast": TunableParam("int", 5, 20, 12),
                "macd_slow": TunableParam("int", 20, 60, 26),
                "macd_signal": TunableParam("int", 5, 20, 9),
            },
            description="MACD line, signal, and histogram",
        ))

        self.register(FeatureSpec(
            name="bollinger",
            columns=["bb_upper", "bb_lower", "bb_middle", "bb_width", "bb_pct"],
            group=FeatureGroup.TECHNICAL,
            tunable_params={
                "bb_period": TunableParam("int", 10, 30, 20),
                "bb_std": TunableParam("float", 1.5, 3.0, 2.0),
            },
            description="Bollinger Bands",
        ))

        self.register(FeatureSpec(
            name="atr",
            columns=["atr"],
            group=FeatureGroup.TECHNICAL,
            tunable_params={
                "atr_period": TunableParam("int", 7, 28, 14),
            },
            description="Average True Range",
        ))

        self.register(FeatureSpec(
            name="adx",
            columns=["adx", "plus_di", "minus_di"],
            group=FeatureGroup.TECHNICAL,
            tunable_params={
                "adx_period": TunableParam("int", 7, 28, 14),
            },
            description="Average Directional Index",
        ))

        self.register(FeatureSpec(
            name="obv",
            columns=["obv", "obv_slope_20d"],
            group=FeatureGroup.TECHNICAL,
            tunable_params={
                "obv_slope_window": TunableParam("int", 10, 40, 20),
            },
            description="On-Balance Volume and slope",
        ))

        # --- Momentum features ---
        self.register(FeatureSpec(
            name="momentum",
            columns=[
                "momentum_score", "mom_1m", "mom_3m", "mom_6m", "mom_12m",
                "momentum_acceleration", "trend_strength",
                "relative_strength", "rel_strength_21d",
                "distance_52w_high", "distance_52w_low",
            ],
            group=FeatureGroup.MOMENTUM,
            depends_on=["returns"],
            description="Momentum composite, relative strength, 52w distance",
        ))

        # --- Mean reversion features ---
        self.register(FeatureSpec(
            name="mean_reversion",
            columns=[
                "zscore_20d", "zscore_60d",
                "distance_to_sma20", "distance_to_sma50",
                "mean_reversion_score",
                "oversold_indicator", "overbought_indicator",
                "bullish_divergence", "bearish_divergence",
            ],
            group=FeatureGroup.MEAN_REVERSION,
            description="Z-scores, SMA distance, divergence indicators",
        ))

        # --- Sentiment features ---
        self.register(FeatureSpec(
            name="sentiment",
            columns=[
                "sentiment_mean_1d", "sentiment_std_1d",
                "sentiment_count_1d", "sentiment_trend_1d",
                "sentiment_mean_7d", "sentiment_std_7d",
                "sentiment_count_7d", "sentiment_trend_7d",
                "sentiment_mean_14d", "sentiment_std_14d",
                "sentiment_count_14d", "sentiment_trend_14d",
            ],
            group=FeatureGroup.SENTIMENT,
            enabled_by_default=False,
            description="News sentiment features (disabled by default)",
        ))

    def register(self, spec: FeatureSpec) -> None:
        """Register a feature specification."""
        self._specs[spec.name] = spec

    def get(self, name: str) -> Optional[FeatureSpec]:
        """Get a feature spec by name."""
        return self._specs.get(name)

    def get_all(self) -> Dict[str, FeatureSpec]:
        """Get all registered feature specs."""
        return dict(self._specs)

    def get_group(self, group: FeatureGroup) -> List[FeatureSpec]:
        """Get all feature specs in a group."""
        return [s for s in self._specs.values() if s.group == group]

    def get_group_names(self) -> List[str]:
        """Get unique group names across all specs."""
        return list({s.group.value for s in self._specs.values()})

    def resolve_dependencies(self, feature_names: List[str]) -> List[str]:
        """Topologically sort features including their dependencies."""
        resolved = []
        visited = set()

        def _visit(name: str) -> None:
            if name in visited:
                return
            visited.add(name)
            spec = self._specs.get(name)
            if spec:
                for dep in spec.depends_on:
                    _visit(dep)
            resolved.append(name)

        for name in feature_names:
            _visit(name)
        return resolved

    def resolve_columns(self, feature_names: List[str]) -> List[str]:
        """Map feature spec names to actual DataFrame column names."""
        all_names = self.resolve_dependencies(feature_names)
        columns = []
        seen = set()
        for name in all_names:
            spec = self._specs.get(name)
            if spec:
                for col in spec.columns:
                    if col not in seen:
                        columns.append(col)
                        seen.add(col)
        return columns

    def get_tunable_params(self, feature_name: str) -> Dict[str, TunableParam]:
        """Get tunable parameters for a feature."""
        spec = self._specs.get(feature_name)
        if spec:
            return spec.tunable_params
        return {}

    def get_default_order(self) -> List[str]:
        """Get the default feature addition order for regression testing."""
        return [f for f in DEFAULT_FEATURE_ORDER if f in self._specs]

    def get_baseline(self) -> List[str]:
        """Get default baseline feature names."""
        return [f for f in DEFAULT_BASELINE if f in self._specs]
