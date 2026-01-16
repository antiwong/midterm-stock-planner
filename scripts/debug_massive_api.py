#!/usr/bin/env python3
"""
Debug Massive API
=================
Debug the Massive API to see what's being returned.
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.api_keys import load_api_keys
import requests

def debug_massive_api():
    """Debug Massive API response."""
    api_keys = load_api_keys()
    api_key = api_keys.get('MASSIVE_API_KEY') or api_keys.get('POLYGON_API_KEY')
    
    if not api_key:
        print("❌ No Massive API key found")
        return
    
    print("=" * 70)
    print("DEBUGGING MASSIVE API")
    print("=" * 70)
    print(f"API Key: {api_key[:8]}...{api_key[-4:]}")
    print()
    
    ticker = "AAPL"
    
    # Try the ratios endpoint
    print(f"1️⃣ Testing Ratios Endpoint for {ticker}...")
    url = "https://api.massive.com/v2/reference/financials/ratios"
    params = {
        'ticker': ticker,
        'apiKey': api_key
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        print(f"   Status Code: {response.status_code}")
        print(f"   Response Headers: {dict(response.headers)}")
        print()
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Response Keys: {list(data.keys())}")
            print()
            
            if 'status' in data:
                print(f"   Status: {data['status']}")
            
            if 'results' in data:
                results = data['results']
                print(f"   Results Type: {type(results)}")
                print(f"   Results Length: {len(results) if isinstance(results, list) else 'N/A'}")
                
                if isinstance(results, list) and len(results) > 0:
                    print(f"   First Result Keys: {list(results[0].keys())}")
                    print()
                    print("   First Result Sample:")
                    print(json.dumps(results[0], indent=2)[:500])
                elif isinstance(results, dict):
                    print(f"   Result Keys: {list(results.keys())}")
                    print()
                    print("   Result Sample:")
                    print(json.dumps(results, indent=2)[:500])
            else:
                print("   Full Response:")
                print(json.dumps(data, indent=2)[:1000])
        else:
            print(f"   Error Response: {response.text[:500]}")
    
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print()
    print("=" * 70)
    
    # Try alternative endpoint - ticker details
    print(f"2️⃣ Testing Ticker Details Endpoint for {ticker}...")
    url2 = "https://api.massive.com/v2/reference/tickers/{ticker}/details"
    url2 = url2.format(ticker=ticker)
    params2 = {
        'apiKey': api_key
    }
    
    try:
        response2 = requests.get(url2, params=params2, timeout=10)
        print(f"   Status Code: {response2.status_code}")
        
        if response2.status_code == 200:
            data2 = response2.json()
            print(f"   Response Keys: {list(data2.keys())}")
            if 'results' in data2:
                print(f"   Results Keys: {list(data2['results'].keys()) if isinstance(data2['results'], dict) else 'N/A'}")
        else:
            print(f"   Error: {response2.text[:500]}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

if __name__ == "__main__":
    debug_massive_api()
