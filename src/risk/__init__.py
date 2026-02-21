"""Risk management module."""

from .complexity import (
    compute_config_complexity,
    compute_factor_redundancy,
    compute_penalty,
    exceeds_thresholds,
)
from .metrics import RiskMetrics
from .position_sizing import PositionSizer
from .portfolio import PortfolioRiskManager
from .risk_parity import (
    RiskParityAllocator,
    RiskAwarePosition,
    PortfolioRiskProfile,
    SectorConstraints,
    generate_risk_report,
)

__all__ = [
    "compute_config_complexity",
    "compute_factor_redundancy",
    "compute_penalty",
    "exceeds_thresholds",
    "RiskMetrics",
    "PositionSizer",
    "PortfolioRiskManager",
    # Risk Parity
    "RiskParityAllocator",
    "RiskAwarePosition", 
    "PortfolioRiskProfile",
    "SectorConstraints",
    "generate_risk_report",
]
