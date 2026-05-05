# 🏆 LEGENDARY ENGINE v2.1 - ALERT SETUP GUIDE

## Telegram Alert Configuration

### Step 1: Create a Telegram Bot
1. Open Telegram and search for `@BotFather`
2. Send `/newbot` command
3. Follow prompts to name your bot
4. Copy the **Bot Token** provided (looks like: `123456789:ABCdefGHI...`)

### Step 2: Get Your Chat ID
1. Search for `@userinfobot` in Telegram
2. Start a chat and send any message
3. It will reply with your **Chat ID** (a number like `123456789`)

### Step 3: Start Receiving Alerts
Start a conversation with your bot (search for it in Telegram and click "Start")

### Step 4: Configure the Engine

**Option A: Environment Variables**
```powershell
$env:TELEGRAM_BOT_TOKEN = "your_bot_token_here"
$env:TELEGRAM_CHAT_ID = "your_chat_id_here"
python start_live_engine.py
```

**Option B: Command Line**
```powershell
python start_live_engine.py --telegram-token "your_token" --telegram-chat "your_chat_id"
```

**Option C: API Request**
```powershell
$body = @{
    mode = "live"
    capital = 500000
    max_positions = 10
    telegram_bot_token = "your_token"
    telegram_chat_id = "your_chat_id"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:5080/api/legendary-engine/start" -Method Post -Body $body -ContentType "application/json"
```

---

## Webhook Configuration (Optional)

For custom integrations (Slack, Discord, custom apps):

```powershell
python start_live_engine.py --webhook "https://your-webhook-url.com/endpoint"
```

Webhook payload format:
```json
{
    "type": "SIGNAL|TRADE_EXECUTED|POSITION_CLOSED|AI_WARNING",
    "symbol": "RELIANCE",
    "timestamp": "2025-12-07T10:30:00",
    ...additional fields
}
```

---

## Alert Types

| Alert | Trigger | Content |
|-------|---------|---------|
| 🎯 Signal Found | When a valid signal is detected | Symbol, RSI, Confirmations, AI Confidence |
| 🚀 Trade Executed | When a trade is placed | Entry, Target, Stop Loss, Quantity |
| ✅/❌ Position Closed | When a position exits | P&L, Exit Reason, Hold Time |
| ⚠️ AI Warning | When AI detects risk | Risk Level, Recommendation |
| 📊 Daily Summary | End of trading day | Win Rate, Total P&L, Stats |

---

## Engine Configuration Summary

| Parameter | Value | Description |
|-----------|-------|-------------|
| Mode | **LIVE** | Real trading (no paper mode) |
| RSI Zones | **28, 38, 39** | Based on Dec 2025 backtest |
| Min Confirmations | **5+** | Lowered for current market |
| Max Positions | **10** | Concurrent trades |
| AI Tiers | **3-Tier** | flash-lite → flash → pro-exp |
| Target | **1.8%** | Per trade |
| Stop Loss | **0.8%** | Per trade |
| Trailing Stop | **0.5%** | Dynamic |

---

## Quick Start Commands

```powershell
# Start with defaults (LIVE mode)
python start_live_engine.py

# Start with Telegram alerts
python start_live_engine.py --telegram-token "BOT_TOKEN" --telegram-chat "CHAT_ID"

# Start without AI (for testing)
python start_live_engine.py --no-ai

# Start via API
Invoke-RestMethod -Uri "http://localhost:5080/api/legendary-engine/start" -Method Post
```

---

## Service Restart (Apply Code Changes)

Open PowerShell as **Administrator**:
```powershell
Restart-Service -Name "EliteEquityHVService" -Force
```
