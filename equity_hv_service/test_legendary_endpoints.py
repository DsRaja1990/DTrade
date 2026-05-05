"""Quick test for Legendary API endpoints"""
import requests
import time

BASE_URL = "http://localhost:5090"

def test_endpoints():
    print("=" * 60)
    print("🧪 Testing Legendary API Endpoints")
    print("=" * 60)
    
    # Test 1: Health
    print("\n1. Testing /health...")
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"   Status: {r.status_code}")
        print(f"   Response: {r.json()}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 2: Status
    print("\n2. Testing /api/legendary/status...")
    try:
        r = requests.get(f"{BASE_URL}/api/legendary/status", timeout=5)
        print(f"   Status: {r.status_code}")
        print(f"   Response: {r.json()}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 3: Signals
    print("\n3. Testing /api/legendary/signals...")
    try:
        r = requests.get(f"{BASE_URL}/api/legendary/signals", timeout=5)
        print(f"   Status: {r.status_code}")
        print(f"   Response: {r.json()}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 4: Scan (POST) - this will take time
    print("\n4. Testing /api/legendary/scan (POST)...")
    print("   This may take 15-20 seconds to fetch market data...")
    try:
        r = requests.post(f"{BASE_URL}/api/legendary/scan", timeout=60)
        print(f"   Status: {r.status_code}")
        result = r.json()
        print(f"   Success: {result.get('success', False)}")
        print(f"   Signals Found: {result.get('signals_found', 0)}")
        if result.get('signals'):
            for s in result['signals'][:3]:  # Show top 3
                print(f"   - {s['symbol']}: RSI {s['rsi']}, {s['confirmations']} confirmations, Score {s['score']}")
    except Exception as e:
        print(f"   Error: {e}")
    
    print("\n" + "=" * 60)
    print("✅ Testing Complete")
    print("=" * 60)

if __name__ == "__main__":
    test_endpoints()
