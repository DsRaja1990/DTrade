"""
Quick Health Check for Trading Services
Tests if both services can start and respond
"""

import requests
import time

def test_gemini_service():
    """Test if gemini_trade_service is running"""
    try:
        response = requests.get("http://localhost:8080/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print("✅ gemini_trade_service: HEALTHY")
            print(f"   Status: {data.get('status')}")
            print(f"   Config Loaded: {data.get('config_loaded')}")
            return True
        else:
            print(f"❌ gemini_trade_service: ERROR (Status {response.status_code})")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ gemini_trade_service: NOT RUNNING")
        return False
    except Exception as e:
        print(f"❌ gemini_trade_service: ERROR - {e}")
        return False

def test_config_endpoints():
    """Test configuration endpoints"""
    try:
        # Test config status
        response = requests.get("http://localhost:8080/config/status", timeout=5)
        if response.status_code == 200:
            print("✅ Config API: WORKING")
            return True
        else:
            print(f"⚠️  Config API: Status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Config API: ERROR - {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("TRADING SERVICES - HEALTH CHECK")
    print("=" * 60)
    print()
    
    print("Testing gemini_trade_service...")
    gemini_ok = test_gemini_service()
    print()
    
    if gemini_ok:
        print("Testing configuration endpoints...")
        config_ok = test_config_endpoints()
        print()
    
    print("=" * 60)
    if gemini_ok:
        print("✅ RESULT: Service is operational!")
    else:
        print("❌ RESULT: Service needs debugging")
    print("=" * 60)
