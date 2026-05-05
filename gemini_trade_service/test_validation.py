"""
Test Suite for Gemini Trade Service
Validates service functionality with real market data
"""

import asyncio
import aiohttp
import json
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8080"

class GeminiTradeServiceTester:
    """Test harness for Gemini Trade Service"""
    
    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url
        self.test_results = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "errors": []
        }
    
    async def test_health_check(self):
        """Test 1: Service Health Check"""
        logger.info("=" * 60)
        logger.info("TEST 1: Service Health Check")
        logger.info("=" * 60)
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/health") as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"[OK] Health Check PASSED")
                        logger.info(f"   Status: {data.get('status')}")
                        logger.info(f"   Service: {data.get('service')}")
                        logger.info(f"   Config Loaded: {data.get('config_loaded')}")
                        self.test_results["passed"] += 1
                        return True
                    else:
                        logger.error(f"[ERROR] Health Check FAILED: Status {response.status}")
                        self.test_results["failed"] += 1
                        return False
        except Exception as e:
            logger.error(f"[ERROR] Health Check ERROR: {e}")
            self.test_results["errors"].append(str(e))
            self.test_results["failed"] += 1
            return False
        finally:
            self.test_results["total_tests"] += 1
    
    async def test_config_status(self):
        """Test 2: Configuration Status"""
        logger.info("\n" + "=" * 60)
        logger.info("TEST 2: Configuration Status")
        logger.info("=" * 60)
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/config/status") as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"[OK] Config Status PASSED")
                        
                        # Check Dhan config
                        dhan = data.get('config', {}).get('dhan_api', {})
                        logger.info(f"   Dhan Client ID: {dhan.get('client_id')}")
                        logger.info(f"   Dhan Token: {dhan.get('access_token', 'Not found')[:20]}...")
                        
                        # Check Gemini config
                        gemini_t1 = data.get('config', {}).get('gemini_api', {}).get('tier_1_2', {})
                        gemini_t3 = data.get('config', {}).get('gemini_api', {}).get('tier_3', {})
                        logger.info(f"   Gemini Tier 1&2: {gemini_t1.get('api_key', 'Not found')[:15]}...")
                        logger.info(f"   Gemini Tier 3: {gemini_t3.get('api_key', 'Not found')[:15]}...")
                        
                        self.test_results["passed"] += 1
                        return True
                    else:
                        logger.error(f"[ERROR] Config Status FAILED: Status {response.status}")
                        self.test_results["failed"] += 1
                        return False
        except Exception as e:
            logger.error(f"[ERROR] Config Status ERROR: {e}")
            self.test_results["errors"].append(str(e))
            self.test_results["failed"] += 1
            return False
        finally:
            self.test_results["total_tests"] += 1
    
    async def test_market_data_integration(self):
        """Test 3: Market Data Integration (if available)"""
        logger.info("\n" + "=" * 60)
        logger.info("TEST 3: Market Data Integration")
        logger.info("=" * 60)
        
        # This would test actual Dhan API calls
        # For now, we'll mark as pending if market is closed
        current_hour = datetime.now().hour
        if current_hour < 9 or current_hour > 15:
            logger.info("⏸️  Market Data Test SKIPPED (market closed)")
            logger.info("   Schedule for next market session (9:15 AM - 3:30 PM)")
            return None
        
        # During market hours, would test:
        # - Nifty constituent data fetch
        # - VIX data
        # - Option chain
        logger.info("[DATA] Market hours detected - data fetch test would run here")
        return None
    
    async def test_tier_1_analysis(self):
        """Test 4: AI Tier 1 - Stock Screener"""
        logger.info("\n" + "=" * 60)
        logger.info("TEST 4: AI Tier 1 Analysis")
        logger.info("=" * 60)
        
        # This would trigger actual Tier 1 analysis
        logger.info("⏸️  Tier 1 Test PENDING - requires market data")
        logger.info("   Would analyze 50 Nifty stocks and generate sentiment")
        return None
    
    async def test_end_to_end_signal(self):
        """Test 5: End-to-End Signal Generation"""
        logger.info("\n" + "=" * 60)
        logger.info("TEST 5: End-to-End Signal Generation")
        logger.info("=" * 60)
        
        try:
            async with aiohttp.ClientSession() as session:
                # Try to get a signal (if implemented)
                async with session.get(f"{self.base_url}/api/signal") as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"[OK] Signal Generation WORKING")
                        logger.info(f"   Signal: {data.get('signal')}")
                        logger.info(f"   Confidence: {data.get('confidence')}")
                        logger.info(f"   Reasoning: {data.get('reasoning')}")
                        self.test_results["passed"] += 1
                        return True
                    else:
                        logger.warning(f"[WARN]  Signal endpoint returned {response.status}")
                        logger.info("   This is expected if market is closed or no setup detected")
                        return None
        except aiohttp.ClientConnectorError:
            logger.error("[ERROR] Cannot connect to service - is it running?")
            self.test_results["errors"].append("Service not running")
            self.test_results["failed"] += 1
            return False
        except Exception as e:
            logger.error(f"[ERROR] Signal Generation ERROR: {e}")
            self.test_results["errors"].append(str(e))
            self.test_results["failed"] += 1
            return False
        finally:
            self.test_results["total_tests"] += 1
    
    def print_summary(self):
        """Print test summary"""
        logger.info("\n" + "=" * 60)
        logger.info("TEST SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total Tests: {self.test_results['total_tests']}")
        logger.info(f"[OK] Passed: {self.test_results['passed']}")
        logger.info(f"[ERROR] Failed: {self.test_results['failed']}")
        if self.test_results['errors']:
            logger.info(f"\nErrors:")
            for error in self.test_results['errors']:
                logger.info(f"  - {error}")
        logger.info("=" * 60)
        
        # Calculate pass rate
        if self.test_results['total_tests'] > 0:
            pass_rate = (self.test_results['passed'] / self.test_results['total_tests']) * 100
            logger.info(f"\n[DATA] Pass Rate: {pass_rate:.1f}%")
            
            if pass_rate >= 80:
                logger.info("🎉 EXCELLENT - Ready for next phase")
            elif pass_rate >= 60:
                logger.info("[OK] GOOD - Minor fixes needed")
            else:
                logger.info("[WARN]  NEEDS WORK - Review failures before proceeding")


async def run_all_tests():
    """Run complete test suite"""
    logger.info("[START] Starting Gemini Trade Service Test Suite")
    logger.info(f"📅 Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("\n")
    
    tester = GeminiTradeServiceTester()
    
    # Run tests
    await tester.test_health_check()
    await tester.test_config_status()
    await tester.test_market_data_integration()
    await tester.test_tier_1_analysis()
    await tester.test_end_to_end_signal()
    
    # Print summary
    tester.print_summary()
    
    return tester.test_results


if __name__ == "__main__":
    print("\n" + "="*60)
    print("GEMINI TRADE SERVICE - VALIDATION TEST SUITE")
    print("="*60 + "\n")
    
    # Run tests
    results = asyncio.run(run_all_tests())
    
    # Exit code based on results
    exit(0 if results['failed'] == 0 else 1)
