"""
Test suite for Integration Progress System (Phase 3A.1)

Tests biological-technological integration tracking, filter risk modifiers,
and low-integration penalties.
"""

import sys
from pathlib import Path

# Add src directory to path
src_path = Path(__file__).parent.parent / 'src'
sys.path.insert(0, str(src_path))

from integration_progress import IntegrationProgress


def test_integration_initialization():
    """Test that integration system initializes correctly"""
    integration = IntegrationProgress()
    assert integration.integration_level == 0.0
    assert integration.crisis_threshold == 0.3
    assert integration.high_integration_threshold == 0.7
    print("✓ Integration initialization test passed")


def test_integration_increases_from_tech():
    """Test that integration increases when techs are researched"""
    integration = IntegrationProgress()
    
    # Research Synthetic Biology (+30%)
    integration.add_integration(0.3, "Synthetic Biology")
    assert integration.integration_level == 0.3
    
    # Research Neural Interface (+40%)
    integration.add_integration(0.4, "Neural Interface")
    assert integration.integration_level == 0.7
    
    # Research Consciousness Upload (+60%), should cap at 1.0
    integration.add_integration(0.6, "Consciousness Upload")
    assert integration.integration_level == 1.0
    
    print("✓ Integration increases test passed")


def test_low_integration_increases_filter_risk():
    """Test that low integration (<0.3) increases self-destruct risk"""
    integration = IntegrationProgress()
    
    # At 0% integration (low)
    modifier = integration.get_filter_risk_modifier()
    assert modifier == 1.5, f"Expected 1.5x risk at 0% integration, got {modifier}"
    
    # Add small amount (still under 0.3)
    integration.add_integration(0.2, "Partial Integration")
    modifier = integration.get_filter_risk_modifier()
    assert modifier == 1.5, f"Expected 1.5x risk at 20% integration, got {modifier}"
    
    print("✓ Low integration risk modifier test passed")


def test_high_integration_reduces_filter_risk():
    """Test that high integration (>0.7) reduces self-destruct risk"""
    integration = IntegrationProgress()
    
    # Reach high integration
    integration.add_integration(0.8, "High Integration")
    
    modifier = integration.get_filter_risk_modifier()
    assert modifier == 0.7, f"Expected 0.7x risk at 80% integration, got {modifier}"
    
    print("✓ High integration risk reduction test passed")


def test_medium_integration_neutral():
    """Test that medium integration (0.3-0.7) has neutral effect"""
    integration = IntegrationProgress()
    
    # Reach medium integration
    integration.add_integration(0.5, "Medium Integration")
    
    modifier = integration.get_filter_risk_modifier()
    assert modifier == 1.0, f"Expected 1.0x risk at 50% integration, got {modifier}"
    
    print("✓ Medium integration neutral modifier test passed")


def test_low_integration_penalties():
    """Test that low integration applies multiple penalties"""
    integration = IntegrationProgress()
    
    # At 0% integration (low)
    support_penalty = integration.get_support_penalty()
    assert support_penalty == -10.0, f"Expected -10% support penalty, got {support_penalty}"
    
    research_efficiency = integration.get_research_efficiency()
    assert research_efficiency == 0.85, f"Expected 0.85 research efficiency, got {research_efficiency}"
    
    can_research_tier5 = integration.can_research_tier5()
    assert can_research_tier5 == False, f"Expected Tier 5 locked at low integration"
    
    print("✓ Low integration penalties test passed")


def test_integration_status():
    """Test that integration status returns correct information"""
    integration = IntegrationProgress()
    
    # Low integration
    status = integration.get_integration_status()
    assert status['status'] == "CRISIS"
    assert status['level'] == 0.0
    assert status['filter_risk_modifier'] == 1.5
    
    # Medium integration
    integration.add_integration(0.5, "Test")
    status = integration.get_integration_status()
    assert status['status'] == "TRANSITIONING"
    
    # High integration
    integration.add_integration(0.3, "Test 2")
    status = integration.get_integration_status()
    assert status['status'] == "INTEGRATED"
    
    print("✓ Integration status test passed")


def test_tier5_unlock():
    """Test that Tier 5 technologies unlock at 40% integration"""
    integration = IntegrationProgress()
    
    # Below threshold
    assert integration.can_research_tier5() == False
    
    # Add integration to reach threshold
    integration.add_integration(0.4, "Test")
    assert integration.can_research_tier5() == True
    
    print("✓ Tier 5 unlock test passed")


def test_integration_events_tracked():
    """Test that integration events are tracked for history"""
    integration = IntegrationProgress()
    
    integration.add_integration(0.3, "Synthetic Biology")
    integration.add_integration(0.4, "Neural Interface")
    
    status = integration.get_integration_status()
    assert status['milestone_count'] == 2
    assert len(status['events']) == 2
    assert status['events'][0]['source'] == "Synthetic Biology"
    assert status['events'][1]['source'] == "Neural Interface"
    
    print("✓ Integration event tracking test passed")


def run_all_tests():
    """Run all integration progress tests"""
    print("\n" + "="*60)
    print("INTEGRATION PROGRESS SYSTEM TEST SUITE")
    print("="*60 + "\n")
    
    test_integration_initialization()
    test_integration_increases_from_tech()
    test_low_integration_increases_filter_risk()
    test_high_integration_reduces_filter_risk()
    test_medium_integration_neutral()
    test_low_integration_penalties()
    test_integration_status()
    test_tier5_unlock()
    test_integration_events_tracked()
    
    print("\n" + "="*60)
    print("ALL TESTS PASSED ✓")
    print("="*60 + "\n")


if __name__ == "__main__":
    run_all_tests()
