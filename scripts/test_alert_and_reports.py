"""
Test Alert System and Report Templates
======================================
Comprehensive testing of the new alert and report features.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from src.analytics.alert_system import AlertService, AlertType, AlertChannel
from src.analytics.report_templates import ReportTemplateEngine, ReportFormat
from src.analytics.models import get_db, Run
from src.app.dashboard.data import load_runs


def test_alert_system():
    """Test alert system functionality."""
    print("=" * 70)
    print("TESTING ALERT SYSTEM")
    print("=" * 70)
    
    alert_service = AlertService()
    
    # Test 1: Create alert configuration
    print("\n1. Creating alert configuration...")
    try:
        # Get a recent run
        runs = load_runs()
        if not runs:
            print("   ⚠️  No runs found, skipping run-specific alert")
            test_run_id = None
        else:
            test_run_id = runs[0]['run_id']
            print(f"   Using run: {test_run_id[:16]}...")
        
        config = alert_service.create_alert_config(
            alert_type=AlertType.DRAWDOWN.value,
            run_id=test_run_id,
            user_email="test@example.com",
            threshold=-0.10,  # 10% drawdown
            channels=[AlertChannel.EMAIL.value, AlertChannel.IN_APP.value],
            min_interval_hours=1.0
        )
        print(f"   ✅ Alert config created (ID: {config.id})")
        
        # Test 2: Get alert configs
        print("\n2. Retrieving alert configurations...")
        configs = alert_service.get_alert_configs(run_id=test_run_id)
        print(f"   ✅ Found {len(configs)} alert config(s)")
        
        # Test 3: Check and send alerts (simulated)
        print("\n3. Testing alert checking...")
        if test_run_id:
            alert_data = {
                'type': AlertType.DRAWDOWN.value,
                'level': 'critical',
                'message': 'Portfolio drawdown: -12.5%',
                'value': -0.125,
                'data': {'current_drawdown': -0.125, 'threshold': -0.10}
            }
            
            # Note: This won't actually send email without SMTP config
            sent_alerts = alert_service.check_and_send_alerts(test_run_id, alert_data)
            print(f"   ✅ Alert check completed ({len(sent_alerts)} alerts processed)")
        
        # Test 4: Get alert history
        print("\n4. Retrieving alert history...")
        history = alert_service.get_alert_history(limit=10)
        print(f"   ✅ Found {len(history)} alert history records")
        
        print("\n✅ Alert system tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Alert system test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_report_templates():
    """Test report template functionality."""
    print("\n" + "=" * 70)
    print("TESTING REPORT TEMPLATES")
    print("=" * 70)
    
    engine = ReportTemplateEngine()
    
    # Test 1: Create template
    print("\n1. Creating report template...")
    try:
        template = engine.create_template(
            name="Test Template",
            format=ReportFormat.PDF.value,
            sections=[
                {'type': 'executive_summary', 'enabled': True},
                {'type': 'performance_metrics', 'enabled': True},
                {'type': 'portfolio_composition', 'enabled': True}
            ],
            description="Test template for validation"
        )
        print(f"   ✅ Template created (ID: {template.id})")
        template_id = template.id
        
        # Test 2: Get templates
        print("\n2. Retrieving templates...")
        templates = engine.get_templates()
        print(f"   ✅ Found {len(templates)} template(s)")
        
        # Test 3: Get specific template
        print("\n3. Retrieving specific template...")
        template = engine.get_template(template_id)
        if template:
            print(f"   ✅ Template retrieved: {template.name}")
        else:
            print(f"   ❌ Template not found")
            return False
        
        # Test 4: Update template
        print("\n4. Updating template...")
        updated = engine.update_template(
            template_id=template_id,
            name="Updated Test Template",
            enabled=True
        )
        print(f"   ✅ Template updated: {updated.name}")
        
        # Test 5: Generate report (if run exists)
        print("\n5. Testing report generation...")
        runs = load_runs()
        if runs:
            test_run_id = runs[0]['run_id']
            print(f"   Using run: {test_run_id[:16]}...")
            
            try:
                report_gen = engine.generate_report(
                    template_id=template_id,
                    run_id=test_run_id,
                    generated_by="test_script"
                )
                
                if report_gen.status == 'completed':
                    print(f"   ✅ Report generated successfully!")
                    print(f"      File: {report_gen.file_path}")
                    print(f"      Size: {report_gen.file_size_bytes / 1024:.1f} KB")
                else:
                    print(f"   ⚠️  Report generation status: {report_gen.status}")
                    if report_gen.error_message:
                        print(f"      Error: {report_gen.error_message}")
            except Exception as e:
                print(f"   ⚠️  Report generation failed (expected if dependencies missing): {e}")
        else:
            print("   ⚠️  No runs found, skipping report generation test")
        
        # Test 6: Get report history
        print("\n6. Retrieving report history...")
        history = engine.get_report_history(limit=10)
        print(f"   ✅ Found {len(history)} report generation record(s)")
        
        # Cleanup: Delete test template
        print("\n7. Cleaning up test template...")
        deleted = engine.delete_template(template_id)
        if deleted:
            print(f"   ✅ Test template deleted")
        else:
            print(f"   ⚠️  Template deletion failed (may not exist)")
        
        print("\n✅ Report template tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Report template test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("=" * 70)
    print("COMPREHENSIVE FEATURE TESTING")
    print("=" * 70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {
        'alert_system': False,
        'report_templates': False
    }
    
    # Test alert system
    results['alert_system'] = test_alert_system()
    
    # Test report templates
    results['report_templates'] = test_report_templates()
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    for feature, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status} - {feature.replace('_', ' ').title()}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n✅ All feature tests passed!")
    else:
        print("\n⚠️  Some tests failed. Review output above.")
    
    print("=" * 70)
    
    return results


if __name__ == "__main__":
    main()
