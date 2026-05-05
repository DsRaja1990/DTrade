# Quick Reference - Service Control Endpoints

## AI Scalping Service (Port 4002)

### Start Service
```bash
curl -X POST http://localhost:4002/start \
  -H "Content-Type: application/json" \
  -d '{"mode":"paper","capital":150000,"max_daily_loss":0.04}'
```

### Stop Service
```bash
curl -X POST http://localhost:4002/stop
```

### Update Config
```bash
curl -X PUT http://localhost:4002/config \
  -H "Content-Type: application/json" \
  -d '{"capital":200000,"max_daily_loss":0.03}'
```

### Get Status
```bash
curl http://localhost:4002/status
```

### Get Config
```bash
curl http://localhost:4002/config
```

---

## AI Options Hedger (Port 4003)

### Start Service
```bash
curl -X POST http://localhost:4003/start \
  -H "Content-Type: application/json" \
  -d '{"mode":"paper","capital":250000,"max_daily_loss":0.025}'
```

### Stop Service
```bash
curl -X POST http://localhost:4003/stop
```

### Update Config
```bash
curl -X PUT http://localhost:4003/config \
  -H "Content-Type: application/json" \
  -d '{"capital":300000,"max_daily_loss":0.02}'
```

### Get Status
```bash
curl http://localhost:4003/status
```

### Get Config
```bash
curl http://localhost:4003/config
```

---

## Elite Equity HV (Port 5080)

### Start Service
```bash
curl -X POST http://localhost:5080/api/start \
  -H "Content-Type: application/json" \
  -d '{"mode":"paper","capital":100000,"max_daily_loss":0.05}'
```

### Stop Service
```bash
curl -X POST http://localhost:5080/api/stop
```

### Update Config
```bash
curl -X PUT http://localhost:5080/api/config \
  -H "Content-Type: application/json" \
  -d '{"capital":150000,"max_daily_loss":0.04}'
```

### Get Status
```bash
curl http://localhost:5080/api/status
```

### Get Config
```bash
curl http://localhost:5080/api/config
```

---

## PowerShell Examples

### Test All Services
```powershell
# Check status of all services
$scalp = Invoke-RestMethod "http://localhost:4002/status"
$hedge = Invoke-RestMethod "http://localhost:4003/status"
$equity = Invoke-RestMethod "http://localhost:5080/health"

Write-Host "Scalping: Running=$($scalp.running)"
Write-Host "Hedger: Running=$($hedge.running)"
Write-Host "Equity: $($equity.status)"
```

### Update Capital
```powershell
# Update Scalping capital
$body = @{
  capital = 200000
  max_daily_loss = 0.03
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:4002/config" `
  -Method Put `
  -Body $body `
  -ContentType "application/json"
```

### Start/Stop Services
```powershell
# Start Hedger
$body = @{
  mode = "paper"
  capital = 250000
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:4003/start" `
  -Method Post `
  -Body $body `
  -ContentType "application/json"

# Stop Hedger
Invoke-RestMethod -Uri "http://localhost:4003/stop" -Method Post
```

---

## Frontend TypeScript Examples

### Service Control Class
```typescript
class TradingServiceControl {
  async startService(
    serviceUrl: string,
    config: {
      mode: 'paper' | 'live';
      capital: number;
      max_daily_loss: number;
    }
  ) {
    const response = await fetch(`${serviceUrl}/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config)
    });
    return response.json();
  }

  async stopService(serviceUrl: string) {
    const response = await fetch(`${serviceUrl}/stop`, {
      method: 'POST'
    });
    return response.json();
  }

  async updateConfig(
    serviceUrl: string,
    config: {
      capital: number;
      max_daily_loss: number;
    }
  ) {
    const response = await fetch(`${serviceUrl}/config`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config)
    });
    return response.json();
  }

  async getStatus(serviceUrl: string) {
    const response = await fetch(`${serviceUrl}/status`);
    return response.json();
  }

  async getConfig(serviceUrl: string) {
    const response = await fetch(`${serviceUrl}/config`);
    return response.json();
  }
}

// Usage
const service = new TradingServiceControl();

// Start Scalping Service
await service.startService('http://localhost:4002', {
  mode: 'paper',
  capital: 150000,
  max_daily_loss: 0.04
});

// Update Hedger Capital
await service.updateConfig('http://localhost:4003', {
  capital: 250000,
  max_daily_loss: 0.025
});
```

---

## Response Formats

### Success Response (Start/Stop)
```json
{
  "success": true,
  "message": "Service started",
  "running": true
}
```

### Config Response
```json
{
  "capital": 150000,
  "max_daily_loss": 0.04,
  "paper_trading": true,
  "instruments": ["NIFTY", "BANKNIFTY"],
  "stop_loss_pct": 1.5,
  "target_pct": 0.8
}
```

### Status Response
```json
{
  "running": true,
  "mode": "paper",
  "is_trading_time": true,
  "daily_trades": 5,
  "positions": {
    "position_count": 2,
    "unrealized_pnl": 1500.0,
    "realized_pnl": 3200.0
  },
  "timestamp": "2025-12-12T15:30:00"
}
```

### Error Response
```json
{
  "detail": "Service not initialized"
}
```

---

## Service Management

### Restart All Services (Admin)
```powershell
.\Restart-AI-Services.ps1
```

### Individual Service Restart
```powershell
Restart-Service AIScalpingService -Force
Restart-Service AIOptionsHedger -Force
Restart-Service EliteEquityHVService -Force
```

### Check Service Ports
```powershell
Test-NetConnection -ComputerName localhost -Port 4002
Test-NetConnection -ComputerName localhost -Port 4003
Test-NetConnection -ComputerName localhost -Port 5080
```

---

## Notes

- All endpoints return JSON responses
- Capital is in Indian Rupees (₹)
- Max daily loss is a decimal (0.05 = 5%)
- Mode can be: "paper", "live", or "evaluation"
- Services auto-start when Windows services start
- Configuration changes persist during runtime
- Each service has independent capital management
