"""
Dashboard Data Access Layer
===========================
Centralized data access for database queries and file operations.
"""

import pandas as pd
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from src.analytics.models import get_db, Run, StockScore, Trade, PortfolioSnapshot, CustomWatchlist
from .utils import get_project_root, get_run_folder


def clean_and_deduplicate_symbols(symbols: List[str]) -> List[str]:
    """
    Clean and deduplicate a list of ticker symbols.
    
    - Converts to uppercase
    - Removes duplicates (preserving order)
    - Removes empty strings and whitespace
    - Validates basic ticker format
    
    Args:
        symbols: Raw list of ticker symbols
        
    Returns:
        Cleaned and deduplicated list
    """
    seen = set()
    cleaned = []
    
    for symbol in symbols:
        # Clean the symbol
        s = str(symbol).strip().upper()
        
        # Skip empty
        if not s:
            continue
        
        # Basic validation: alphanumeric with optional . or -
        import re
        if not re.match(r'^[A-Z0-9\.\-]{1,10}$', s):
            continue
        
        # Deduplicate
        if s not in seen:
            seen.add(s)
            cleaned.append(s)
    
    return cleaned


def validate_watchlist_symbols(symbols: List[str], check_existence: bool = True) -> Dict[str, Any]:
    """
    Validate watchlist symbols and return validation report.
    
    Args:
        symbols: List of ticker symbols to validate
        check_existence: Whether to check if symbols actually exist (default: True)
        
    Returns:
        Dictionary with validation results:
        - valid_symbols: List of valid symbols (format + existence if check_existence=True)
        - duplicates: List of duplicate symbols removed
        - invalid: List of invalid symbols removed (format issues)
        - non_existent: List of symbols that don't exist (if check_existence=True)
        - warnings: List of warning messages
    """
    original_count = len(symbols)
    cleaned = []
    duplicates = []
    invalid = []
    seen = set()
    
    import re
    
    for symbol in symbols:
        s = str(symbol).strip().upper()
        
        # Skip empty
        if not s:
            continue
        
        # Basic validation
        if not re.match(r'^[A-Z0-9\.\-]{1,10}$', s):
            invalid.append(symbol)
            continue
        
        # Check duplicates
        if s in seen:
            duplicates.append(s)
            continue
        
        seen.add(s)
        cleaned.append(s)
    
    warnings = []
    if duplicates:
        warnings.append(f"Removed {len(duplicates)} duplicate symbols")
    if invalid:
        warnings.append(f"Removed {len(invalid)} invalid symbols")
    
    result = {
        'valid_symbols': cleaned,
        'original_count': original_count,
        'final_count': len(cleaned),
        'duplicates': duplicates,
        'invalid': invalid,
        'warnings': warnings,
    }
    
    # Check existence if requested
    if check_existence and cleaned:
        try:
            from .symbol_validator import validate_symbols_batch
            existence_check = validate_symbols_batch(cleaned)
            
            # Update result with existence check
            result['existence_check'] = existence_check
            result['valid_symbols'] = existence_check['valid_symbols']  # Only keep existing symbols
            result['non_existent'] = existence_check['invalid_symbols']
            result['unknown_symbols'] = existence_check['unknown_symbols']
            result['final_count'] = len(existence_check['valid_symbols'])
            
            if existence_check['invalid_symbols']:
                warnings.append(f"{len(existence_check['invalid_symbols'])} symbols do not exist and were removed")
            if existence_check['unknown_symbols']:
                warnings.append(f"{len(existence_check['unknown_symbols'])} symbols could not be validated")
            
            result['warnings'] = warnings
            
        except Exception as e:
            # If existence check fails, log but don't fail
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Symbol existence check failed: {e}")
            result['existence_check_error'] = str(e)
    
    return result


def get_database():
    """Get database connection (no caching to ensure fresh data).
    
    Returns:
        Database instance
    """
    db_path = get_project_root() / "data" / "analysis.db"
    return get_db(str(db_path))


def load_runs() -> List[Dict[str, Any]]:
    """Load all runs from database (fresh each time).
    
    Returns:
        List of run dictionaries
    """
    db = get_database()
    session = db.get_session()
    try:
        runs = session.query(Run).order_by(Run.created_at.desc()).all()
        return [r.to_dict() for r in runs]
    finally:
        session.close()


def load_run_by_id(run_id: str) -> Optional[Dict[str, Any]]:
    """Load a specific run by ID.
    
    Args:
        run_id: Run ID to load
    
    Returns:
        Run dictionary or None
    """
    db = get_database()
    session = db.get_session()
    try:
        run = session.query(Run).filter_by(run_id=run_id).first()
        return run.to_dict() if run else None
    finally:
        session.close()


def load_run_scores(run_id: str) -> List[Dict[str, Any]]:
    """Load scores for a specific run.
    
    Args:
        run_id: Run ID
    
    Returns:
        List of score dictionaries
    """
    db = get_database()
    session = db.get_session()
    try:
        scores = session.query(StockScore).filter_by(run_id=run_id).order_by(StockScore.rank).all()
        return [s.to_dict() for s in scores]
    finally:
        session.close()


def load_run_trades(run_id: str) -> List[Dict[str, Any]]:
    """Load trades for a specific run.
    
    Args:
        run_id: Run ID
    
    Returns:
        List of trade dictionaries
    """
    db = get_database()
    session = db.get_session()
    try:
        trades = session.query(Trade).filter_by(run_id=run_id).order_by(Trade.date).all()
        return [t.to_dict() for t in trades]
    finally:
        session.close()


def load_portfolio_snapshots(run_id: str) -> List[Dict[str, Any]]:
    """Load portfolio snapshots for a specific run.
    
    Args:
        run_id: Run ID
    
    Returns:
        List of snapshot dictionaries
    """
    db = get_database()
    session = db.get_session()
    try:
        snapshots = session.query(PortfolioSnapshot).filter_by(run_id=run_id).order_by(PortfolioSnapshot.date).all()
        return [s.to_dict() for s in snapshots]
    finally:
        session.close()


def delete_run(run_id: str) -> bool:
    """Delete a run and all associated data.
    
    Args:
        run_id: Run ID to delete
    
    Returns:
        True if successful
    """
    db = get_database()
    session = db.get_session()
    try:
        # Delete associated records
        session.query(StockScore).filter_by(run_id=run_id).delete()
        session.query(Trade).filter_by(run_id=run_id).delete()
        session.query(PortfolioSnapshot).filter_by(run_id=run_id).delete()
        session.query(Run).filter_by(run_id=run_id).delete()
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def get_runs_with_folders() -> List[Dict[str, Any]]:
    """Get runs with their folder status.
    
    Returns:
        List of run dictionaries with folder info
    """
    runs = load_runs()
    output_base = get_project_root() / "output"
    
    for run in runs:
        run_id_short = run['run_id'][:16]
        watchlist = run.get('watchlist')
        
        # Try watchlist-prefixed folder first
        if watchlist:
            run_folder = output_base / f"run_{watchlist}_{run_id_short}"
        else:
            run_folder = output_base / f"run_{run_id_short}"
        
        # If not found, search for any matching folder
        if not run_folder.exists():
            for folder in output_base.iterdir():
                if folder.is_dir() and run_id_short in folder.name:
                    run_folder = folder
                    break
        
        run['has_folder'] = run_folder.exists()
        run['folder_path'] = str(run_folder) if run_folder.exists() else None
        run['file_count'] = len(list(run_folder.iterdir())) if run_folder.exists() else 0
    
    return runs


def get_available_run_folders() -> List[Dict[str, Any]]:
    """Get list of available run folders.
    
    Returns:
        List of folder info dictionaries
    """
    output_base = get_project_root() / "output"
    if not output_base.exists():
        return []
    
    folders = []
    for folder in output_base.iterdir():
        if folder.is_dir() and folder.name.startswith('run_'):
            files = list(folder.iterdir())
            
            # Parse folder name to extract watchlist and run_id
            # Format: run_{watchlist}_{YYYYMMDD_HHMMSS_hash} or run_{YYYYMMDD_HHMMSS_hash}
            name_without_prefix = folder.name.replace('run_', '')
            name_parts = name_without_prefix.split('_')
            
            watchlist = None
            run_id = name_without_prefix
            
            # Find the date part (YYYYMMDD format, starts with 20)
            date_idx = None
            for i, part in enumerate(name_parts):
                if len(part) == 8 and part.startswith('20') and part.isdigit():
                    date_idx = i
                    break
            
            if date_idx is not None and date_idx > 0:
                # Everything before the date is the watchlist name
                watchlist = '_'.join(name_parts[:date_idx])
                run_id = '_'.join(name_parts[date_idx:])
            
            folders.append({
                'name': folder.name,
                'path': str(folder),
                'run_id': run_id,
                'watchlist': watchlist,
                'file_count': len(files),
                'files': [f.name for f in files],
                'modified': datetime.fromtimestamp(folder.stat().st_mtime)
            })
    
    return sorted(folders, key=lambda x: x['modified'], reverse=True)


def load_backtest_metrics(run_id: str) -> Optional[Dict[str, Any]]:
    """Load backtest metrics for a run.
    
    Args:
        run_id: Run ID
    
    Returns:
        Metrics dictionary or None
    """
    run_folder = get_run_folder(run_id)
    metrics_file = run_folder / "backtest_metrics.json"
    
    if metrics_file.exists():
        with open(metrics_file) as f:
            return json.load(f)
    
    # Try legacy location
    legacy_file = get_project_root() / "output" / "backtest_metrics.json"
    if legacy_file.exists():
        with open(legacy_file) as f:
            return json.load(f)
    
    return None


def load_backtest_returns(run_id: str) -> Optional[pd.DataFrame]:
    """Load backtest returns for a run.
    
    Args:
        run_id: Run ID
    
    Returns:
        Returns DataFrame or None
    """
    run_folder = get_run_folder(run_id)
    returns_file = run_folder / "backtest_returns.csv"
    
    if returns_file.exists():
        return pd.read_csv(returns_file, parse_dates=['date'])
    
    # Try legacy location
    legacy_file = get_project_root() / "output" / "backtest_returns.csv"
    if legacy_file.exists():
        return pd.read_csv(legacy_file, parse_dates=['date'])
    
    return None


def load_backtest_positions(run_id: str) -> Optional[pd.DataFrame]:
    """Load backtest positions for a run.
    
    Args:
        run_id: Run ID
    
    Returns:
        Positions DataFrame or None
    """
    run_folder = get_run_folder(run_id)
    positions_file = run_folder / "backtest_positions.csv"
    
    if positions_file.exists():
        return pd.read_csv(positions_file)
    
    # Try legacy location
    legacy_file = get_project_root() / "output" / "backtest_positions.csv"
    if legacy_file.exists():
        return pd.read_csv(legacy_file)
    
    return None


def load_vertical_candidates(run_id: str) -> List[pd.DataFrame]:
    """Load vertical analysis candidates for a run.
    
    Args:
        run_id: Run ID
    
    Returns:
        List of candidate DataFrames by sector
    """
    run_folder = get_run_folder(run_id)
    if not run_folder.exists():
        return []
    
    candidates = []
    for f in run_folder.glob("vertical_candidates_*.csv"):
        df = pd.read_csv(f)
        df['source_file'] = f.name
        candidates.append(df)
    
    return candidates


def load_horizontal_portfolio(run_id: str) -> Optional[pd.DataFrame]:
    """Load horizontal portfolio for a run.
    
    Args:
        run_id: Run ID
    
    Returns:
        Portfolio DataFrame or None
    """
    run_folder = get_run_folder(run_id)
    
    # Look for horizontal portfolio files
    for pattern in ["horizontal_portfolio_*.csv", "optimized_portfolio_*.csv"]:
        files = list(run_folder.glob(pattern))
        if files:
            # Return most recent
            latest = max(files, key=lambda f: f.stat().st_mtime)
            return pd.read_csv(latest)
    
    return None


def load_ai_commentary(run_id: str) -> Optional[str]:
    """Load AI commentary for a run.
    
    Args:
        run_id: Run ID
    
    Returns:
        Commentary text or None
    """
    run_folder = get_run_folder(run_id)
    
    # Look for AI files
    for pattern in ["ai_commentary*.md", "ai_analysis*.md", "*_recommendations*.md"]:
        files = list(run_folder.glob(pattern))
        if files:
            with open(files[0]) as f:
                return f.read()
    
    return None


def load_ai_recommendations(run_id: str) -> Optional[Dict[str, Any]]:
    """Load AI recommendations for a run.
    
    Args:
        run_id: Run ID
    
    Returns:
        Recommendations dictionary or None
    """
    run_folder = get_run_folder(run_id)
    
    if not run_folder.exists():
        return None
    
    # Look for recommendation JSON files (multiple patterns)
    patterns = [
        "recommendations_*.json",  # Main pattern: recommendations_RUNID_TIMESTAMP.json
        "*_recommendations*.json",
        "ai_recommendations*.json",
        "recommendation*.json",
    ]
    
    for pattern in patterns:
        files = list(run_folder.glob(pattern))
        if files:
            # Get the most recent file if multiple exist
            files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            try:
                with open(files[0]) as f:
                    return json.load(f)
            except Exception as e:
                continue
    
    return None


def load_analysis_report(run_id: str) -> Optional[Dict[str, Any]]:
    """Load analysis report for a run (includes data validation).
    
    Args:
        run_id: Run ID
    
    Returns:
        Analysis report dictionary or None
    """
    run_folder = get_run_folder(run_id)
    
    if not run_folder.exists():
        return None
    
    # Look for analysis report JSON
    patterns = [
        "analysis_report_*.json",
        "*_report_*.json",
    ]
    
    for pattern in patterns:
        files = list(run_folder.glob(pattern))
        if files:
            files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            try:
                with open(files[0]) as f:
                    return json.load(f)
            except Exception:
                continue
    
    return None


def load_data_validation_report(run_id: str) -> Optional[Dict[str, Any]]:
    """Load data validation report for a run.
    
    Args:
        run_id: Run ID
    
    Returns:
        Data validation dictionary or None
    """
    # First try from analysis report
    analysis_report = load_analysis_report(run_id)
    if analysis_report and 'data_validation' in analysis_report:
        return analysis_report['data_validation']
    
    # Then try standalone validation report
    run_folder = get_run_folder(run_id)
    if not run_folder.exists():
        return None
    
    files = list(run_folder.glob("data_validation_*.json"))
    if files:
        files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        try:
            with open(files[0]) as f:
                report = json.load(f)
                return report.get('validation', report)
        except Exception:
            pass
    
    return None


def get_run_summary(run_id: str) -> Dict[str, Any]:
    """Get comprehensive summary for a run.
    
    Args:
        run_id: Run ID
    
    Returns:
        Summary dictionary with all available data
    """
    run = load_run_by_id(run_id)
    if not run:
        return {}
    
    run_folder = get_run_folder(run_id)
    
    summary = {
        'run': run,
        'has_folder': run_folder.exists(),
        'folder_path': str(run_folder) if run_folder.exists() else None,
        'files': [],
        'stages': {
            'backtest': False,
            'enrichment': False,
            'domain_analysis': False,
            'ai_analysis': False,
        }
    }
    
    if run_folder.exists():
        files = list(run_folder.iterdir())
        summary['files'] = [f.name for f in files]
        
        # Check stages
        summary['stages']['backtest'] = any('backtest' in f.name.lower() for f in files)
        summary['stages']['enrichment'] = any('enriched' in f.name.lower() for f in files)
        summary['stages']['domain_analysis'] = any('vertical' in f.name.lower() or 'horizontal' in f.name.lower() for f in files)
        summary['stages']['ai_analysis'] = any('ai' in f.name.lower() or 'commentary' in f.name.lower() for f in files)
    
    return summary


def get_all_tickers() -> List[str]:
    """Get all unique tickers from the database.
    
    Returns:
        List of ticker symbols
    """
    db = get_database()
    session = db.get_session()
    try:
        tickers = session.query(StockScore.ticker).distinct().all()
        return sorted([t[0] for t in tickers])
    finally:
        session.close()


def get_all_sectors() -> List[str]:
    """Get all unique sectors from the database.
    
    Returns:
        List of sector names
    """
    db = get_database()
    session = db.get_session()
    try:
        sectors = session.query(StockScore.sector).distinct().filter(StockScore.sector.isnot(None)).all()
        return sorted([s[0] for s in sectors if s[0]])
    finally:
        session.close()


def load_watchlists() -> Dict[str, Dict[str, Any]]:
    """Load all available watchlists from config.
    
    Returns:
        Dictionary of watchlist_id -> watchlist info
    """
    from src.data.watchlists import WatchlistManager
    
    try:
        config_dir = get_project_root() / "config"
        wl_manager = WatchlistManager.from_config_dir(str(config_dir))
        
        result = {}
        for wl_id, wl in wl_manager.watchlists.items():
            result[wl_id] = {
                'id': wl_id,
                'name': wl.name,
                'description': wl.description,
                'category': wl.category,
                'symbols': wl.symbols,
                'count': len(wl.symbols),
            }
        
        return result
    except Exception as e:
        print(f"Error loading watchlists: {e}")
        return {}


def load_watchlist_by_id(watchlist_id: str) -> Optional[Dict[str, Any]]:
    """Load a specific watchlist by ID.
    
    Args:
        watchlist_id: Watchlist identifier (e.g., 'tech_giants')
    
    Returns:
        Watchlist info dictionary or None
    """
    watchlists = load_watchlists()
    return watchlists.get(watchlist_id)


def get_watchlist_categories() -> Dict[str, List[str]]:
    """Get watchlists grouped by category.
    
    Returns:
        Dictionary of category -> list of watchlist IDs
    """
    watchlists = load_watchlists()
    categories = {}
    
    for wl_id, wl in watchlists.items():
        category = wl.get('category', 'custom')
        if category not in categories:
            categories[category] = []
        categories[category].append(wl_id)
    
    return categories


def get_default_watchlist() -> str:
    """Get the default watchlist ID.
    
    Returns:
        Default watchlist ID
    """
    from src.data.watchlists import WatchlistManager
    
    try:
        config_dir = get_project_root() / "config"
        wl_manager = WatchlistManager.from_config_dir(str(config_dir))
        return wl_manager.default_watchlist
    except Exception:
        return 'tech_giants'


# =============================================================================
# CUSTOM WATCHLIST CRUD OPERATIONS
# =============================================================================

def load_custom_watchlists() -> List[Dict[str, Any]]:
    """Load all custom watchlists from database.
    
    Returns:
        List of custom watchlist dictionaries
    """
    db = get_database()
    session = db.get_session()
    try:
        watchlists = session.query(CustomWatchlist).order_by(CustomWatchlist.name).all()
        return [w.to_dict() for w in watchlists]
    finally:
        session.close()


def load_custom_watchlist_by_id(watchlist_id: str) -> Optional[Dict[str, Any]]:
    """Load a specific custom watchlist by ID.
    
    Args:
        watchlist_id: Watchlist identifier
    
    Returns:
        Watchlist dictionary or None
    """
    db = get_database()
    session = db.get_session()
    try:
        watchlist = session.query(CustomWatchlist).filter_by(watchlist_id=watchlist_id).first()
        return watchlist.to_dict() if watchlist else None
    finally:
        session.close()


def create_custom_watchlist(
    watchlist_id: str,
    name: str,
    symbols: List[str],
    description: str = "",
    category: str = "custom",
    source_watchlists: List[str] = None,
    is_default: bool = False,
) -> Dict[str, Any]:
    """Create a new custom watchlist with automatic deduplication and validation.
    
    Args:
        watchlist_id: Unique identifier for the watchlist
        name: Display name
        symbols: List of ticker symbols (will be cleaned and deduplicated)
        description: Optional description
        category: Category (default: 'custom')
        source_watchlists: List of source watchlist IDs used to create this
        is_default: Whether this is the default watchlist
    
    Returns:
        Created watchlist dictionary with additional 'validation' key
    
    Raises:
        ValueError: If watchlist_id already exists
    """
    # Clean and deduplicate symbols, and check existence
    validation = validate_watchlist_symbols(symbols, check_existence=True)
    cleaned_symbols = validation['valid_symbols']
    
    # Warn if symbols were removed
    if validation.get('non_existent'):
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Removed {len(validation['non_existent'])} non-existent symbols: {validation['non_existent'][:10]}")
    
    db = get_database()
    session = db.get_session()
    try:
        # Check if ID already exists
        existing = session.query(CustomWatchlist).filter_by(watchlist_id=watchlist_id).first()
        if existing:
            raise ValueError(f"Watchlist ID '{watchlist_id}' already exists")
        
        # If setting as default, unset other defaults
        if is_default:
            session.query(CustomWatchlist).filter_by(is_default=True).update({'is_default': False})
        
        watchlist = CustomWatchlist(
            watchlist_id=watchlist_id,
            name=name,
            description=description,
            category=category,
            is_default=is_default,
        )
        watchlist.set_symbols(cleaned_symbols)
        watchlist.set_source_watchlists(source_watchlists or [])
        
        session.add(watchlist)
        session.commit()
        
        result = watchlist.to_dict()
        result['validation'] = validation
        return result
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def update_custom_watchlist(
    watchlist_id: str,
    name: str = None,
    symbols: List[str] = None,
    description: str = None,
    category: str = None,
    source_watchlists: List[str] = None,
    is_default: bool = None,
) -> Optional[Dict[str, Any]]:
    """Update an existing custom watchlist with automatic deduplication.
    
    Args:
        watchlist_id: Watchlist identifier to update
        name: New display name (optional)
        symbols: New list of ticker symbols (optional, will be cleaned and deduplicated)
        description: New description (optional)
        category: New category (optional)
        source_watchlists: New source watchlist IDs (optional)
        is_default: Set as default (optional)
    
    Returns:
        Updated watchlist dictionary with 'validation' key if symbols were updated, or None if not found
    """
    validation = None
    
    db = get_database()
    session = db.get_session()
    try:
        watchlist = session.query(CustomWatchlist).filter_by(watchlist_id=watchlist_id).first()
        if not watchlist:
            return None
        
        if name is not None:
            watchlist.name = name
        if description is not None:
            watchlist.description = description
        if category is not None:
            watchlist.category = category
        if symbols is not None:
            # Clean and deduplicate symbols, and check existence
            validation = validate_watchlist_symbols(symbols, check_existence=True)
            watchlist.set_symbols(validation['valid_symbols'])
            
            # Warn if symbols were removed
            if validation.get('non_existent'):
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Removed {len(validation['non_existent'])} non-existent symbols from {watchlist_id}: {validation['non_existent'][:10]}")
        if source_watchlists is not None:
            watchlist.set_source_watchlists(source_watchlists)
        if is_default is not None:
            if is_default:
                # Unset other defaults
                session.query(CustomWatchlist).filter(
                    CustomWatchlist.watchlist_id != watchlist_id,
                    CustomWatchlist.is_default == True
                ).update({'is_default': False})
            watchlist.is_default = is_default
        
        session.commit()
        result = watchlist.to_dict()
        if validation:
            result['validation'] = validation
        return result
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def delete_custom_watchlist(watchlist_id: str) -> bool:
    """Delete a custom watchlist.
    
    Args:
        watchlist_id: Watchlist identifier to delete
    
    Returns:
        True if deleted, False if not found
    """
    db = get_database()
    session = db.get_session()
    try:
        watchlist = session.query(CustomWatchlist).filter_by(watchlist_id=watchlist_id).first()
        if not watchlist:
            return False
        
        session.delete(watchlist)
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def add_symbols_to_custom_watchlist(watchlist_id: str, symbols: List[str]) -> Optional[Dict[str, Any]]:
    """Add symbols to an existing custom watchlist.
    
    Args:
        watchlist_id: Watchlist identifier
        symbols: Symbols to add
    
    Returns:
        Updated watchlist dictionary or None if not found
    """
    db = get_database()
    session = db.get_session()
    try:
        watchlist = session.query(CustomWatchlist).filter_by(watchlist_id=watchlist_id).first()
        if not watchlist:
            return None
        
        current_symbols = watchlist.get_symbols()
        new_symbols = list(dict.fromkeys(current_symbols + [s.upper() for s in symbols]))
        watchlist.set_symbols(new_symbols)
        
        session.commit()
        return watchlist.to_dict()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def remove_symbols_from_custom_watchlist(watchlist_id: str, symbols: List[str]) -> Optional[Dict[str, Any]]:
    """Remove symbols from a custom watchlist.
    
    Args:
        watchlist_id: Watchlist identifier
        symbols: Symbols to remove
    
    Returns:
        Updated watchlist dictionary or None if not found
    """
    db = get_database()
    session = db.get_session()
    try:
        watchlist = session.query(CustomWatchlist).filter_by(watchlist_id=watchlist_id).first()
        if not watchlist:
            return None
        
        symbols_to_remove = set(s.upper() for s in symbols)
        current_symbols = watchlist.get_symbols()
        new_symbols = [s for s in current_symbols if s.upper() not in symbols_to_remove]
        watchlist.set_symbols(new_symbols)
        
        session.commit()
        return watchlist.to_dict()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def create_watchlist_from_sources(
    watchlist_id: str,
    name: str,
    source_watchlist_ids: List[str],
    description: str = "",
) -> Dict[str, Any]:
    """Create a custom watchlist by combining multiple source watchlists.
    
    Args:
        watchlist_id: Unique identifier for the new watchlist
        name: Display name
        source_watchlist_ids: List of watchlist IDs to combine
        description: Optional description
    
    Returns:
        Created watchlist dictionary
    """
    # Load symbols from all source watchlists
    all_symbols = []
    
    # Load from standard watchlists (YAML)
    standard_watchlists = load_watchlists()
    
    # Load from custom watchlists (DB)
    custom_watchlists = {w['watchlist_id']: w for w in load_custom_watchlists()}
    
    for source_id in source_watchlist_ids:
        # Check standard watchlists first
        if source_id in standard_watchlists:
            all_symbols.extend(standard_watchlists[source_id].get('symbols', []))
        # Then check custom watchlists
        elif source_id in custom_watchlists:
            all_symbols.extend(custom_watchlists[source_id].get('symbols', []))
    
    # Remove duplicates while preserving order
    unique_symbols = list(dict.fromkeys(all_symbols))
    
    return create_custom_watchlist(
        watchlist_id=watchlist_id,
        name=name,
        symbols=unique_symbols,
        description=description,
        category='custom',
        source_watchlists=source_watchlist_ids,
    )


def get_all_available_watchlists() -> Dict[str, Dict[str, Any]]:
    """Get all available watchlists (both standard and custom).
    
    Returns:
        Dictionary of watchlist_id -> watchlist info
    """
    # Load standard watchlists from YAML
    watchlists = load_watchlists()
    
    # Load custom watchlists from database
    custom = load_custom_watchlists()
    for wl in custom:
        wl_id = wl['watchlist_id']
        # Mark as custom and editable
        wl['is_custom'] = True
        wl['editable'] = True
        watchlists[wl_id] = wl
    
    # Mark standard watchlists as non-editable
    for wl_id in watchlists:
        if 'is_custom' not in watchlists[wl_id]:
            watchlists[wl_id]['is_custom'] = False
            watchlists[wl_id]['editable'] = False
    
    return watchlists
