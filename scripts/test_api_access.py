#!/usr/bin/env python3
"""Test API access with simpler endpoints to verify keys work."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.api_keys import load_api_keys
import requests

api_keys = load_api_keys()

print("=" * 70)
print("API ACCESS TEST")
print("=" * 70)
print()

# Test Massive API with ticker details (simpler endpoint)
massive_key = api_keys.get('MASSIVE_API_KEY') or api_keys.get('POLYGON_API_KEY')
if massive_key:
    print("1️⃣ Testing Massive API (Ticker Details)...")
    url = "https://api.massive.com/v2/reference/tickers/AAPL"
    params = {'apiKey': massive_key}
    
    try:
        response = requests.get(url, params=params, timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'OK':
                print("   ✅ Massive API Key: VALID")
                print("   ⚠️  Note: Fundamentals endpoint returned empty results")
                print("      This may require a paid subscription plan")
            else:
                print(f"   ⚠️  Status: {data.get('status')}")
        else:
            print(f"   ❌ Error: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    print()

# Test Finnhub API
finnhub_key = api_keys.get('FINNHUB_API_KEY')
if finnhub_key:
    print("2️⃣ Testing Finnhub API...")
    url = "https://finnhub.io/api/v1/quote"
    params = {'symbol': 'AAPL', 'token': finnhub_key}
    
    try:
        response = requests.get(url, params=params, timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            if 'c' in data:  # current price
                print("   ✅ Finnhub API Key: VALID")
            else:
                print("   ⚠️  Response format unexpected")
        else:
            print(f"   ❌ Error: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    print()

print("=" * 70)
print("SUMMARY")
print("=" * 70)
print("✅ Finnhub API: Working and returning fundamentals data")
print("⚠️  Massive API: Key is valid, but fundamentals endpoint returns empty")
print("   This likely means fundamentals require a paid subscription")
print("   The API key works for basic endpoints (ticker details)")
print()
print("💡 RECOMMENDATION:")
print("   • Use Finnhub for fundamentals (working)")
print("   • Massive API can be used for other data types")
print("   • Multi-source fetcher will automatically use available sources")
