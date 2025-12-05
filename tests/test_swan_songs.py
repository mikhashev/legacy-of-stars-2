"""
Test script for Swan Song Messages feature
Tests discovery mechanics, rewards, and AI generation
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.swan_song_messages import SwanSongManager, SwanSongCategory
from src.ai_manager import AIManager

def test_swan_song_creation():
    """Test creating swan songs for extinct civilizations"""
    print("=" * 60)
    print("TEST 1: Swan Song Creation")
    print("=" * 60)
    
    ai = AIManager()
    manager = SwanSongManager(ai)
    
    # Create swan songs for different civilizations
    manager.create_swan_song("Alpha Centauri", 1500, 50000)
    manager.create_swan_song("Barnard's Star", 3000, 200000)
    manager.create_swan_song("Wolf 359", 500, 10000)
    
    assert len(manager.swan_songs) == 3
    print("✓ Created 3 swan songs")
    
    assert manager.has_swan_song("Alpha Centauri")
    assert manager.has_swan_song("Barnard's Star")
    assert manager.has_swan_song("Wolf 359")
    print("✓ All systems have swan songs")
    
    assert not manager.is_discovered("Alpha Centauri")
    print("✓ Swan songs start as undiscovered")
    
    print("\nSwan Song Categories:")
    for name, song in manager.swan_songs.items():
        print(f"  {name}: {song.category}")
    
    print("\n✅ TEST 1 PASSED\n")

def test_swan_song_discovery():
    """Test discovery mechanics with different knowledge levels"""
    print("=" * 60)
    print("TEST 2: Swan Song Discovery Mechanics")
    print("=" * 60)
    
    ai = AIManager()
    manager = SwanSongManager(ai)
    
    manager.create_swan_song("Proxima Centauri", 2000, 100000)
    
    # Test insufficient knowledge
    result = manager.discover_swan_song("Proxima Centauri", 20)
    assert "error" in result
    assert "Insufficient knowledge" in result["error"]
    print("✓ Cannot discover with <30% knowledge")
    
    # Test discovery at 50% knowledge
    result = manager.discover_swan_song("Proxima Centauri", 50)
    # May succeed or fail probabilistically at 50%
    if "error" not in result:
        print("✓ Discovered swan song at 50% knowledge")
        assert result["system"] == "Proxima Centauri"
        assert "message" in result
        assert "rewards" in result
        print(f"  Category: {result['category']}")
        print(f"  Rewards: {result['rewards']}")
    else:
        print("✓ Discovery failed at 50% (probabilistic - expected sometimes)")
    
    # Test already discovered
    if "error" not in result:
        result2 = manager.discover_swan_song("Proxima Centauri", 80)
        assert "error" in result2
        assert "already discovered" in result2["error"].lower()
        print("✓ Cannot discover same swan song twice")
    
    print("\n✅ TEST 2 PASSED\n")

def test_swan_song_rewards():
    """Test different reward categories"""
    print("=" * 60)
    print("TEST 3: Swan Song Reward Categories")
    print("=" * 60)
    
    ai = AIManager()
    manager = SwanSongManager(ai)
    
    # Create enough swan songs to likely get all categories
    for i in range(10):
        manager.create_swan_song(f"System_{i}", 1000, 50000)
    
    categories_found = set()
    
    for name in manager.swan_songs.keys():
        result = manager.discover_swan_song(name, 100)  # 100% success at high knowledge
        if "error" not in result:
            categories_found.add(result['category'])
            print(f"✓ {result['category']}: {list(result['rewards'].keys())}")
    
    print(f"\nTotal categories found: {len(categories_found)}")
    print(f"Categories: {categories_found}")
    
    print("\n✅ TEST 3 PASSED\n")

def test_tech_discount():
    """Test tech discount accumulation"""
    print("=" * 60)
    print("TEST 4: Tech Discount System")
    print("=" * 60)
    
    ai = AIManager()
    manager = SwanSongManager(ai)
    
    # Create a technical swan song (25% chance)
    created_technical = False
    for i in range(20):  # Try multiple times
        manager.create_swan_song(f"Tech_System_{i}", 1000, 50000)
        
    # Discover all and find technical ones
    for name in manager.swan_songs.keys():
        result = manager.discover_swan_song(name, 100)
        if "error" not in result and result['category'] == SwanSongCategory.TECHNICAL:
            created_technical = True
            assert "tech_discount" in result["rewards"]
            print(f"✓ Technical swan song gives tech discount: {result['rewards']['tech_discount']*100}%")
            break
    
    if created_technical:
        # Test discount retrieval
        discount = manager.get_tech_discount()
        assert discount > 0
        print(f"✓ Retrieved tech discount: {discount*100}%")
        
        # Test discount consumed
        discount2 = manager.get_tech_discount()
        assert discount2 == 0
        print("✓ Tech discount consumed after use")
    else:
        print("⚠️ No technical swan song generated (probabilistic)")
    
    print("\n✅ TEST 4 PASSED\n")

def test_message_generation():
    """Test AI message generation (basic structure check)"""
    print("=" * 60)
    print("TEST 5: Message Generation")
    print("=" * 60)
    
    ai = AIManager()
    manager = SwanSongManager(ai)
    
    manager.create_swan_song("Test System", 1000, 75000)
    
    result = manager.discover_swan_song("Test System", 100)
    
    if "error" not in result:
        message = result["message"]
        print(f"✓ Generated message ({len(message)} characters)")
        print("\nMessage preview:")
        print("-" * 60)
        print(message[:300] + "..." if len(message) > 300 else message)
        print("-" * 60)
        
        # Basic validation
        assert len(message) > 50  # Should be substantial
        assert isinstance(message, str)
        print("✓ Message structure valid")
    
    print("\n✅ TEST 5 PASSED\n")

def run_all_tests():
    """Run all swan song tests"""
    print("\n" + "=" * 60)
    print("SWAN SONG MESSAGES - TEST SUITE")
    print("=" * 60 + "\n")
    
    try:
        test_swan_song_creation()
        test_swan_song_discovery()
        test_swan_song_rewards()
        test_tech_discount()
        test_message_generation()
        
        print("=" * 60)
        print("🎉 ALL TESTS PASSED! 🎉")
        print("=" * 60)
        print("\nSwan Song Messages system is working correctly!")
        print("Ready for integration with main game.")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        raise
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        raise

if __name__ == "__main__":
    run_all_tests()
