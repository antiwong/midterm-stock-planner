#!/usr/bin/env python3
"""
Test Fundamentals API Keys
==========================
Tests if Massive and Finnhub API keys work for downloading fundamentals.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.api_keys import load_api_keys
from src.fundamental.multi_source_fetcher import MultiSourceFundamentalsFetcher

def test_api_keys():
    """Test if API keys are configured."""
    print("=" * 70)
    print("TESTING FUNDAMENTALS API KEYS")
    print("=" * 70)
    print()
    
    # Load API keys
    api_keys = load_api_keys()
    
    print("📋 API Keys Status:")
    print("-" * 70)
    
    massive_key = api_keys.get('MASSIVE_API_KEY') or api_keys.get('POLYGON_API_KEY')
    finnhub_key = api_keys.get('FINNHUB_API_KEY')
    
    if massive_key:
        print(f"✅ Massive API Key: {massive_key[:8]}...{massive_key[-4:]}")
    else:
        print("❌ Massive API Key: Not found")
    
    if finnhub_key:
        print(f"✅ Finnhub API Key: {finnhub_key[:8]}...{finnhub_key[-4:]}")
    else:
        print("❌ Finnhub API Key: Not found")
    
    print()
    
    # Test with a sample ticker
    test_ticker = "AAPL"
    print(f"🧪 Testing with ticker: {test_ticker}")
    print("-" * 70)
    print()
    
    try:
        fetcher = MultiSourceFundamentalsFetcher()
        available_sources = fetcher._get_available_sources()
        
        print(f"📊 Available sources: {', '.join(available_sources)}")
        print()
        
        # Test each source individually
        results = {}
        
        if 'massive' in available_sources:
            print("1️⃣ Testing Massive API...")
            try:
                massive_data = fetcher._fetch_massive(test_ticker)
                if massive_data:
                    non_null_fields = sum(1 for v in massive_data.values() if v is not None)
                    print(f"   ✅ Massive API: Success! Retrieved {non_null_fields} fields")
                    results['massive'] = massive_data
                else:
                    print("   ⚠️  Massive API: No data returned")
                    results['massive'] = None
            except Exception as e:
                print(f"   ❌ Massive API: Error - {e}")
                results['massive'] = None
            print()
        
        if 'finnhub' in available_sources:
            print("2️⃣ Testing Finnhub API...")
            try:
                finnhub_data = fetcher._fetch_finnhub(test_ticker)
                if finnhub_data:
                    non_null_fields = sum(1 for v in finnhub_data.values() if v is not None)
                    print(f"   ✅ Finnhub API: Success! Retrieved {non_null_fields} fields")
                    results['finnhub'] = finnhub_data
                else:
                    print("   ⚠️  Finnhub API: No data returned")
                    results['finnhub'] = None
            except Exception as e:
                print(f"   ❌ Finnhub API: Error - {e}")
                results['finnhub'] = None
            print()
        
        # Test multi-source fetch
        print("3️⃣ Testing Multi-Source Fetch (merges all sources)...")
        try:
            merged_data = fetcher.fetch_fundamentals(test_ticker, sources=['massive', 'finnhub', 'yfinance'])
            if merged_data:
                non_null_fields = sum(1 for v in merged_data.values() if v is not None and v != test_ticker)
                print(f"   ✅ Multi-Source: Success! Merged {non_null_fields} fields")
                print()
                print("   📊 Sample fields retrieved:")
                sample_fields = ['pe', 'pb', 'roe', 'net_margin', 'market_cap']
                for field in sample_fields:
                    value = merged_data.get(field)
                    if value is not None:
                        print(f"      • {field}: {value}")
                results['merged'] = merged_data
            else:
                print("   ⚠️  Multi-Source: No data returned")
                results['merged'] = None
        except Exception as e:
            print(f"   ❌ Multi-Source: Error - {e}")
            results['merged'] = None
        print()
        
        # Summary
        print("=" * 70)
        print("📊 TEST SUMMARY")
        print("=" * 70)
        
        if results.get('massive'):
            print("✅ Massive API: Working")
        elif 'massive' in available_sources:
            print("⚠️  Massive API: Configured but returned no data")
        else:
            print("❌ Massive API: Not configured")
        
        if results.get('finnhub'):
            print("✅ Finnhub API: Working")
        elif 'finnhub' in available_sources:
            print("⚠️  Finnhub API: Configured but returned no data")
        else:
            print("❌ Finnhub API: Not configured")
        
        if results.get('merged'):
            print("✅ Multi-Source Fetch: Working")
        else:
            print("⚠️  Multi-Source Fetch: Partial or no data")
        
        print()
        print("=" * 70)
        
        # Return success if at least one source works
        return results.get('massive') is not None or results.get('finnhub') is not None
        
    except Exception as e:
        print(f"❌ Error testing APIs: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_api_keys()
    sys.exit(0 if success else 1)
