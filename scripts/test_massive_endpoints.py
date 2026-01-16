#!/usr/bin/env python3
"""Test different Massive API endpoint formats."""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.api_keys import load_api_keys
import requests

api_keys = load_api_keys()
api_key = api_keys.get('MASSIVE_API_KEY') or api_keys.get('POLYGON_API_KEY')

ticker = "AAPL"

# Try different endpoint formats
endpoints = [
    ("https://api.massive.com/v2/reference/financials/ratios", {'ticker': ticker, 'apiKey': api_key}),
    ("https://api.polygon.io/v2/reference/financials/ratios", {'ticker': ticker, 'apiKey': api_key}),
    ("https://api.massive.com/v2/reference/financials", {'ticker': ticker, 'apiKey': api_key}),
    ("https://api.polygon.io/v2/reference/financials", {'ticker': ticker, 'apiKey': api_key}),
]

print("Testing different endpoint formats...\n")

for url, params in endpoints:
    print(f"Testing: {url}")
    try:
        response = requests.get(url, params=params, timeout=10)
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            if 'results' in data:
                results = data['results']
                if isinstance(results, list):
                    print(f"  Results: {len(results)} items")
                    if len(results) > 0:
                        print(f"  ✅ SUCCESS! First result keys: {list(results[0].keys())[:5]}")
                        break
                else:
                    print(f"  Results type: {type(results)}")
            else:
                print(f"  Response: {list(data.keys())}")
        else:
            print(f"  Error: {response.text[:200]}")
    except Exception as e:
        print(f"  Exception: {e}")
    print()
