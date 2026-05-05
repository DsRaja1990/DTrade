"""
🏆 LEGENDARY PRODUCTION ENGINE v2.1 - LIVE TRADING STARTUP
==========================================================
This script starts the production engine with full features:
- LIVE trading mode
- RSI zones: 28, 38, 39 (optimized Dec 2025)
- 5+ confirmation threshold
- Telegram/Webhook alerts
- 3-Tier Gemini AI integration
- Multi-position management (up to 10)

USAGE:
  python start_live_engine.py [--telegram-token TOKEN] [--telegram-chat CHAT_ID] [--webhook URL]
"""

import asyncio
import argparse
import os
import sys
import signal
import json
from datetime import datetime

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strategy.legendary_production_engine import (
    LegendaryProductionEngine,
    LegendaryProductionConfig,
    TradingMode
)

# Global engine reference
engine = None

def signal_handler(sig, frame):
    """Handle shutdown signals"""
    print("\n🛑 Shutdown signal received...")
    if engine:
        asyncio.create_task(engine.stop())
    sys.exit(0)

async def main():
    global engine
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Legendary Production Engine v2.1")
    parser.add_argument("--telegram-token", type=str, default="", 
                       help="Telegram bot token for alerts")
    parser.add_argument("--telegram-chat", type=str, default="",
                       help="Telegram chat ID for alerts")
    parser.add_argument("--webhook", type=str, default="",
                       help="Webhook URL for custom integrations")
    parser.add_argument("--capital", type=float, default=500000.0,
                       help="Trading capital (default: 500000)")
    parser.add_argument("--max-positions", type=int, default=10,
                       help="Maximum concurrent positions (default: 10)")
    parser.add_argument("--no-ai", action="store_true",
                       help="Run without 3-Tier Gemini AI")
    
    args = parser.parse_args()
    
    # Environment variable overrides
    telegram_token = args.telegram_token or os.environ.get("TELEGRAM_BOT_TOKEN", "")
    telegram_chat = args.telegram_chat or os.environ.get("TELEGRAM_CHAT_ID", "")
    webhook_url = args.webhook or os.environ.get("WEBHOOK_URL", "")
    
    print("=" * 70)
    print("🏆 LEGENDARY PRODUCTION ENGINE v2.1")
    print("=" * 70)
    print(f"   Mode: LIVE TRADING")
    print(f"   Capital: Rs.{args.capital:,.0f}")
    print(f"   Max Positions: {args.max_positions}")
    print(f"   RSI Zones: [28, 38, 39]")
    print(f"   Min Confirmations: 5+")
    print(f"   Gemini AI: {'DISABLED' if args.no_ai else 'ENABLED (3-Tier)'}")
    print(f"   Telegram: {'CONFIGURED' if telegram_token else 'NOT SET'}")
    print(f"   Webhook: {'CONFIGURED' if webhook_url else 'NOT SET'}")
    print("=" * 70)
    
    # Create configuration
    config = LegendaryProductionConfig(
        mode=TradingMode.LIVE,
        capital=args.capital,
        max_positions=args.max_positions,
        require_tier1_confirmation=not args.no_ai,
        require_tier2_strategy=not args.no_ai,
        require_tier3_prediction=not args.no_ai,
        telegram_bot_token=telegram_token,
        telegram_chat_id=telegram_chat,
        webhook_url=webhook_url,
        enable_alerts=True
    )
    
    # Create engine
    engine = LegendaryProductionEngine(config)
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start the engine
    try:
        await engine.start()
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user...")
        await engine.stop()
    except Exception as e:
        print(f"❌ Error: {e}")
        if engine:
            await engine.stop()
        raise

if __name__ == "__main__":
    print(f"\n📅 Starting at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    asyncio.run(main())
