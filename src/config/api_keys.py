"""
API Keys Management
===================
Load and validate API keys for external services.
"""

import os
from pathlib import Path
from typing import Dict, Optional
import warnings


def _load_dotenv():
    """Load .env file from project root."""
    # Find project root (where .env is located)
    current = Path(__file__).resolve()
    
    # Search for .env going up the directory tree
    for parent in [current.parent, current.parent.parent, current.parent.parent.parent]:
        env_file = parent / ".env"
        if env_file.exists():
            # Parse .env file manually (to avoid python-dotenv dependency)
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        if key and value and key not in os.environ:
                            os.environ[key] = value
            return True
    return False


# Load .env on module import
_load_dotenv()


def load_api_keys() -> Dict[str, Optional[str]]:
    """
    Load API keys from .env file and environment variables.
    
    Priority:
    1. Environment variable (if set)
    2. .env file (loaded on import)
    
    Returns:
        Dictionary of API key names to values
    """
    # Ensure .env is loaded
    _load_dotenv()
    
    keys = {}
    
    key_names = [
        "NEWS_API_KEY",
        "GEMINI_API_KEY", 
        "OPENAI_API_KEY",
        "ALPHA_VANTAGE_API_KEY",
    ]
    
    for name in key_names:
        value = os.environ.get(name)
        keys[name] = value
    
    return keys


def setup_api_keys():
    """
    Setup API keys in the environment.
    Call this at the start of scripts to ensure keys are available.
    """
    keys = load_api_keys()
    
    # Set in environment
    for name, value in keys.items():
        if value:
            os.environ[name] = value
    
    return keys


def get_api_key(name: str) -> Optional[str]:
    """
    Get a specific API key.
    
    Args:
        name: Name of the API key (e.g., "NEWS_API_KEY")
        
    Returns:
        API key value or None if not available
    """
    # Try environment first
    value = os.environ.get(name)
    
    # Fall back to defaults
    if not value and name in _DEFAULT_KEYS:
        value = _DEFAULT_KEYS[name]
    
    return value


def check_api_keys(verbose: bool = True) -> Dict[str, bool]:
    """
    Check which API keys are available.
    
    Args:
        verbose: If True, print status
        
    Returns:
        Dictionary of key name to availability status
    """
    keys = load_api_keys()
    status = {}
    
    if verbose:
        print("API Keys Status:")
        print("-" * 40)
    
    for name, value in keys.items():
        available = value is not None and len(value) > 0
        status[name] = available
        
        if verbose:
            icon = "✅" if available else "❌"
            masked = f"{value[:8]}..." if value and len(value) > 8 else "Not set"
            print(f"  {icon} {name}: {masked}")
    
    return status


def test_api_connections() -> Dict[str, bool]:
    """
    Test actual API connections.
    
    Returns:
        Dictionary of API name to connection success
    """
    import requests
    results = {}
    
    # Test NewsAPI
    news_key = get_api_key("NEWS_API_KEY")
    if news_key:
        try:
            resp = requests.get(
                "https://newsapi.org/v2/everything",
                params={"q": "test", "apiKey": news_key, "pageSize": 1},
                timeout=10
            )
            results["NewsAPI"] = resp.status_code == 200
        except:
            results["NewsAPI"] = False
    
    # Test Gemini
    gemini_key = get_api_key("GEMINI_API_KEY")
    if gemini_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=gemini_key)
            
            # Try different model names
            model = None
            for model_name in ['gemini-2.0-flash-exp', 'gemini-1.5-flash-latest', 'gemini-1.5-pro-latest', 'gemini-pro']:
                try:
                    model = genai.GenerativeModel(model_name)
                    break
                except:
                    continue
            
            if model:
                response = model.generate_content("Say OK")
                results["Gemini"] = True
            else:
                results["Gemini"] = False
        except:
            results["Gemini"] = False
    
    # Test OpenAI
    openai_key = get_api_key("OPENAI_API_KEY")
    if openai_key:
        try:
            import openai
            client = openai.OpenAI(api_key=openai_key)
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "OK"}],
                max_tokens=5
            )
            results["OpenAI"] = True
        except:
            results["OpenAI"] = False
    
    return results


# Auto-setup on import
setup_api_keys()


if __name__ == "__main__":
    print("=" * 50)
    print("API Keys Configuration")
    print("=" * 50)
    
    check_api_keys(verbose=True)
    
    print("\nTesting connections...")
    results = test_api_connections()
    for name, success in results.items():
        icon = "✅" if success else "❌"
        print(f"  {icon} {name}: {'Connected' if success else 'Failed'}")
