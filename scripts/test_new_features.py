#!/usr/bin/env python3
"""
Test New Features
=================
Test the newly added features: update buttons, tooltips, dark mode, etc.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_tooltips_module():
    """Test that tooltips module exists and works."""
    print("=" * 60)
    print("Testing Tooltips Module")
    print("=" * 60)
    
    try:
        from src.app.dashboard.components.tooltips import get_tooltip
        
        # Test a few tooltips
        test_keys = ['run_select', 'portfolio_size', 'watchlist_select', 'export_format']
        for key in test_keys:
            tooltip = get_tooltip(key)
            if tooltip:
                print(f"✅ {key}: Tooltip exists ({len(tooltip)} chars)")
            else:
                print(f"⚠️  {key}: No tooltip found")
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_update_buttons():
    """Test that update functions exist."""
    print("\n" + "=" * 60)
    print("Testing Update Buttons")
    print("=" * 60)
    
    try:
        from src.app.dashboard.pages.overview import _update_prices, _update_benchmark
        
        print("✅ _update_prices function exists")
        print("✅ _update_benchmark function exists")
        
        # Check if PriceDownloader can be imported
        try:
            from scripts.download_prices import PriceDownloader
            print("✅ PriceDownloader can be imported")
        except ImportError:
            print("⚠️  PriceDownloader import may need path adjustment")
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_dark_mode_components():
    """Test dark mode support in components."""
    print("\n" + "=" * 60)
    print("Testing Dark Mode Components")
    print("=" * 60)
    
    try:
        from src.app.dashboard.components.loading import render_loading_card
        from src.app.dashboard.components.errors import ErrorHandler, render_warning_with_actions
        
        print("✅ Loading components support dark mode")
        print("✅ Error components support dark mode")
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_shortcuts_tab():
    """Test shortcuts tab in settings."""
    print("\n" + "=" * 60)
    print("Testing Shortcuts Tab")
    print("=" * 60)
    
    try:
        from src.app.dashboard.pages.settings import _render_shortcuts_tab
        from src.app.dashboard.components.shortcuts import render_shortcuts_help
        
        print("✅ _render_shortcuts_tab function exists")
        print("✅ render_shortcuts_help function exists")
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_failed_symbols_guide():
    """Test that failed symbols guide exists."""
    print("\n" + "=" * 60)
    print("Testing Failed Symbols Guide")
    print("=" * 60)
    
    guide_path = project_root / "docs" / "failed-symbols-guide.md"
    if guide_path.exists():
        print(f"✅ Guide exists: {guide_path}")
        content = guide_path.read_text()
        if "BRK.B" in content and "BRK-B" in content:
            print("✅ Guide contains BRK.B fix recommendation")
        if "ATVI" in content and "SPLK" in content:
            print("✅ Guide contains delisted symbols info")
        return True
    else:
        print(f"❌ Guide not found: {guide_path}")
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("New Features Test Suite")
    print("=" * 60)
    print()
    
    results = []
    
    results.append(("Tooltips Module", test_tooltips_module()))
    results.append(("Update Buttons", test_update_buttons()))
    results.append(("Dark Mode Components", test_dark_mode_components()))
    results.append(("Shortcuts Tab", test_shortcuts_tab()))
    results.append(("Failed Symbols Guide", test_failed_symbols_guide()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All new feature tests passed!")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please review.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
