"""
Database Models for Stock Analysis
===================================
SQLAlchemy models for storing analysis runs, stock scores, and reports.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
import json

from sqlalchemy import (
    create_engine, Column, Integer, String, Float, DateTime, 
    Text, ForeignKey, Boolean, Index, JSON
)
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
from sqlalchemy.ext.mutable import MutableDict, MutableList

Base = declarative_base()

# Note: Extended models in analysis_models.py import Base from here
# This avoids circular imports


class Run(Base):
    """Analysis run record."""
    __tablename__ = 'runs'
    
    id = Column(Integer, primary_key=True)
    run_id = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(200))
    run_type = Column(String(50), nullable=False)  # backtest, score, optimization
    status = Column(String(20), default='in_progress')  # in_progress, completed, failed
    
    # Watchlist used for this run
    watchlist = Column(String(100))  # e.g., 'tech_giants', 'semiconductors'
    watchlist_display_name = Column(String(200))  # Human-readable name
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    duration_seconds = Column(Float)
    
    description = Column(Text)
    tags = Column(Text)  # JSON array
    
    # Configuration
    config_json = Column(Text)  # JSON config snapshot
    
    # Results summary
    total_return = Column(Float)
    sharpe_ratio = Column(Float)
    max_drawdown = Column(Float)
    win_rate = Column(Float)
    hit_rate = Column(Float)
    spearman_corr = Column(Float)
    
    # Universe
    universe_count = Column(Integer)
    universe_json = Column(Text)  # JSON list of tickers
    
    # Additional metrics
    metrics_json = Column(Text)  # JSON for any additional metrics
    
    # Relationships
    scores = relationship("StockScore", back_populates="run", cascade="all, delete-orphan")
    trades = relationship("Trade", back_populates="run", cascade="all, delete-orphan")
    portfolio_history = relationship("PortfolioSnapshot", back_populates="run", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_run_type_status', 'run_type', 'status'),
        Index('idx_run_created', 'created_at'),
        Index('idx_run_watchlist', 'watchlist'),  # For watchlist filtering
        Index('idx_run_status_created', 'status', 'created_at'),  # Common filter combo
    )
    
    def get_tags(self) -> List[str]:
        return json.loads(self.tags) if self.tags else []
    
    def set_tags(self, tags: List[str]):
        self.tags = json.dumps(tags)
    
    def get_config(self) -> Dict:
        return json.loads(self.config_json) if self.config_json else {}
    
    def set_config(self, config: Dict):
        self.config_json = json.dumps(config, default=str)
    
    def get_universe(self) -> List[str]:
        return json.loads(self.universe_json) if self.universe_json else []
    
    def set_universe(self, universe: List[str]):
        self.universe_json = json.dumps(universe)
        self.universe_count = len(universe)
    
    def get_metrics(self) -> Dict:
        return json.loads(self.metrics_json) if self.metrics_json else {}
    
    def set_metrics(self, metrics: Dict):
        self.metrics_json = json.dumps(metrics, default=str)
    
    def to_dict(self) -> Dict:
        return {
            'run_id': self.run_id,
            'name': self.name,
            'run_type': self.run_type,
            'status': self.status,
            'watchlist': self.watchlist,
            'watchlist_display_name': self.watchlist_display_name,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'duration_seconds': self.duration_seconds,
            'description': self.description,
            'tags': self.get_tags(),
            'config': self.get_config(),
            'total_return': self.total_return,
            'sharpe_ratio': self.sharpe_ratio,
            'max_drawdown': self.max_drawdown,
            'win_rate': self.win_rate,
            'hit_rate': self.hit_rate,
            'spearman_corr': self.spearman_corr,
            'universe_count': self.universe_count,
            'metrics': self.get_metrics(),
        }


class StockScore(Base):
    """Individual stock score within a run."""
    __tablename__ = 'stock_scores'
    
    id = Column(Integer, primary_key=True)
    run_id = Column(String(50), ForeignKey('runs.run_id'), nullable=False)
    
    ticker = Column(String(20), nullable=False)
    score = Column(Float, nullable=False)
    rank = Column(Integer)
    percentile = Column(Float)
    
    # Component scores
    tech_score = Column(Float)
    fund_score = Column(Float)
    sent_score = Column(Float)
    
    # Predictions
    predicted_return = Column(Float)
    
    # Additional features
    rsi = Column(Float)
    return_21d = Column(Float)
    return_63d = Column(Float)
    volatility = Column(Float)
    
    # Metadata
    sector = Column(String(100))
    industry = Column(String(100))
    market_cap = Column(Float)
    
    # Extra features as JSON
    features_json = Column(Text)
    
    run = relationship("Run", back_populates="scores")
    
    __table_args__ = (
        Index('idx_score_run_ticker', 'run_id', 'ticker'),
        Index('idx_score_rank', 'run_id', 'rank'),
        Index('idx_score_sector', 'sector'),  # For sector filtering
        Index('idx_score_score', 'score'),  # For score sorting
    )
    
    def get_features(self) -> Dict:
        return json.loads(self.features_json) if self.features_json else {}
    
    def set_features(self, features: Dict):
        self.features_json = json.dumps(features, default=str)
    
    def to_dict(self) -> Dict:
        return {
            'ticker': self.ticker,
            'score': self.score,
            'rank': self.rank,
            'percentile': self.percentile,
            'tech_score': self.tech_score,
            'fund_score': self.fund_score,
            'sent_score': self.sent_score,
            'predicted_return': self.predicted_return,
            'rsi': self.rsi,
            'return_21d': self.return_21d,
            'return_63d': self.return_63d,
            'volatility': self.volatility,
            'sector': self.sector,
            'features': self.get_features(),
        }


class Trade(Base):
    """Trade record for backtesting."""
    __tablename__ = 'trades'
    
    id = Column(Integer, primary_key=True)
    run_id = Column(String(50), ForeignKey('runs.run_id'), nullable=False)
    
    trade_date = Column(DateTime, nullable=False)
    ticker = Column(String(20), nullable=False)
    action = Column(String(10), nullable=False)  # BUY, SELL
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    value = Column(Float)
    commission = Column(Float, default=0)
    
    # Context
    signal_score = Column(Float)
    reason = Column(String(200))
    
    run = relationship("Run", back_populates="trades")
    
    __table_args__ = (
        Index('idx_trade_run_date', 'run_id', 'trade_date'),
    )


class PortfolioSnapshot(Base):
    """Portfolio state at a point in time."""
    __tablename__ = 'portfolio_snapshots'
    
    id = Column(Integer, primary_key=True)
    run_id = Column(String(50), ForeignKey('runs.run_id'), nullable=False)
    
    snapshot_date = Column(DateTime, nullable=False)
    portfolio_value = Column(Float, nullable=False)
    cash = Column(Float)
    equity = Column(Float)
    
    # Performance
    daily_return = Column(Float)
    cumulative_return = Column(Float)
    drawdown = Column(Float)
    
    # Holdings as JSON
    holdings_json = Column(Text)
    
    run = relationship("Run", back_populates="portfolio_history")
    
    __table_args__ = (
        Index('idx_portfolio_run_date', 'run_id', 'snapshot_date'),
    )


class CustomWatchlist(Base):
    """User-defined custom watchlist stored in database."""
    __tablename__ = 'custom_watchlists'
    
    id = Column(Integer, primary_key=True)
    watchlist_id = Column(String(100), unique=True, nullable=False, index=True)  # Unique identifier
    name = Column(String(200), nullable=False)
    description = Column(Text)
    category = Column(String(50), default='custom')
    
    # Symbols as JSON array
    symbols_json = Column(Text, nullable=False)  # JSON list of ticker symbols
    
    # Source watchlists used to create this (JSON array of watchlist IDs)
    source_watchlists_json = Column(Text)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Is this the active/default watchlist?
    is_default = Column(Boolean, default=False)
    
    # Additional settings as JSON
    settings_json = Column(Text)
    
    __table_args__ = (
        Index('idx_custom_watchlist_category', 'category'),
    )
    
    def get_symbols(self) -> list:
        """Get list of symbols."""
        return json.loads(self.symbols_json) if self.symbols_json else []
    
    def set_symbols(self, symbols: list):
        """Set list of symbols."""
        # Ensure uppercase and unique
        unique_symbols = list(dict.fromkeys([s.upper() for s in symbols]))
        self.symbols_json = json.dumps(unique_symbols)
    
    def get_source_watchlists(self) -> list:
        """Get list of source watchlist IDs."""
        return json.loads(self.source_watchlists_json) if self.source_watchlists_json else []
    
    def set_source_watchlists(self, watchlists: list):
        """Set list of source watchlist IDs."""
        self.source_watchlists_json = json.dumps(watchlists)
    
    def get_settings(self) -> dict:
        """Get settings dictionary."""
        return json.loads(self.settings_json) if self.settings_json else {}
    
    def set_settings(self, settings: dict):
        """Set settings dictionary."""
        self.settings_json = json.dumps(settings)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'watchlist_id': self.watchlist_id,
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'symbols': self.get_symbols(),
            'source_watchlists': self.get_source_watchlists(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_default': self.is_default,
            'settings': self.get_settings(),
            'count': len(self.get_symbols()),
        }


class WatchlistStock(Base):
    """Stock in a watchlist with cached data."""
    __tablename__ = 'watchlist_stocks'
    
    id = Column(Integer, primary_key=True)
    ticker = Column(String(20), nullable=False, unique=True)
    
    company_name = Column(String(200))
    sector = Column(String(100))
    industry = Column(String(100))
    market_cap = Column(Float)
    
    # Latest prices
    current_price = Column(Float)
    price_updated_at = Column(DateTime)
    
    # Latest fundamentals
    pe_ratio = Column(Float)
    pb_ratio = Column(Float)
    ps_ratio = Column(Float)
    roe = Column(Float)
    profit_margin = Column(Float)
    revenue_growth = Column(Float)
    dividend_yield = Column(Float)
    fundamentals_updated_at = Column(DateTime)
    
    # Latest sentiment
    sentiment_score = Column(Float)
    sentiment_articles = Column(Integer)
    sentiment_updated_at = Column(DateTime)
    
    # Watchlists this stock belongs to
    watchlists = Column(Text)  # JSON list
    
    __table_args__ = (
        Index('idx_watchlist_sector', 'sector'),
    )


class DatabaseManager:
    """Manages database connections and sessions."""
    
    def __init__(self, db_path: str = "data/analysis.db"):
        self.db_path = db_path
        # Create engine with connection pooling and optimizations
        self.engine = create_engine(
            f'sqlite:///{db_path}',
            echo=False,
            pool_pre_ping=True,  # Verify connections before using
            pool_size=5,  # Connection pool size
            max_overflow=10,  # Max overflow connections
            connect_args={
                'check_same_thread': False,  # Allow multi-threaded access
                'timeout': 20,  # Connection timeout
            }
        )
        # Use scoped_session for thread safety
        from sqlalchemy.orm import scoped_session
        self.Session = scoped_session(sessionmaker(bind=self.engine))
        self._create_tables()
        self._run_migrations()
    
    def _create_tables(self):
        """Create all tables if they don't exist."""
        Base.metadata.create_all(self.engine)
    
    def _run_migrations(self):
        """Run database migrations for schema updates."""
        from sqlalchemy import text, inspect
        
        inspector = inspect(self.engine)
        
        # Check if 'runs' table exists and needs migration
        if 'runs' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('runs')]
            
            with self.engine.connect() as conn:
                # Add watchlist column if missing
                if 'watchlist' not in columns:
                    try:
                        conn.execute(text("ALTER TABLE runs ADD COLUMN watchlist VARCHAR(100)"))
                        conn.commit()
                    except Exception:
                        pass  # Column might already exist
                
                # Add watchlist_display_name column if missing
                if 'watchlist_display_name' not in columns:
                    try:
                        conn.execute(text("ALTER TABLE runs ADD COLUMN watchlist_display_name VARCHAR(200)"))
                        conn.commit()
                    except Exception:
                        pass  # Column might already exist
    
    def get_session(self):
        """Get a new database session."""
        return self.Session()
    
    def close(self):
        """Close the database connection."""
        self.engine.dispose()


# Singleton instance
_db_manager = None

def get_db(db_path: str = "data/analysis.db") -> DatabaseManager:
    """Get or create the database manager singleton."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager(db_path)
    return _db_manager
