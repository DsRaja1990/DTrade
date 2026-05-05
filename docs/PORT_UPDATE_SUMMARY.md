# 🔄 Port Numbers Updated to 4xxx Series

## ✅ Changes Completed

All service ports have been updated from **8xxx** to **4xxx** series to avoid conflicts with your existing services.

---

## 📊 New Port Configuration

| Service | Old Port | New Port | Status |
|---------|----------|----------|--------|
| **Gemini Trade Service** | 8080 | **4080** | ✅ Updated |
| **Elite Equity HV Service** | 8013 | **4013** | ✅ Updated |
| **Your Existing Service** | 8003 | 8003 | Unchanged |

---

## 📝 Files Updated

### Service Configuration Files
1. ✅ `gemini_trade_service/main.py` - Default port: 4080
2. ✅ `gemini_trade_service/ai_signal_client.py` - Service URL: http://localhost:4080
3. ✅ `equity_hv_service/ai_signal_client_integration.py` - Service URL: http://localhost:4080
4. ✅ `equity_hv_service/run_elite_service.py` - Default port: 4013

### Installation Scripts
5. ✅ `gemini_trade_service/install_gemini_service.bat` - Port 4080
6. ✅ `equity_hv_service/install_elite_service.bat` - Port 4013
7. ✅ `equity_hv_service/manage_services.bat` - Updated port references

---

## 🚀 Installation Steps (UNCHANGED)

The installation process remains the same:

```cmd
cd c:\Users\Dhanasimmaraja\Documents\TradeApp\DTrade\equity_hv_service
manage_services.bat → Press '3' → Install BOTH Services
```

---

## 🌐 New Web Interfaces

### Gemini Trade Service
- **Health Check**: http://localhost:4080/health
- **API Endpoint**: http://localhost:4080/api/signal

### Elite Equity HV Service
- **Health Check**: http://localhost:4013/health
- **Dashboard**: http://localhost:4013/

### Your Existing Service (Unchanged)
- **Port**: 8003
- **Status**: Not affected by these changes

---

## 🔧 Service Management

All commands remain the same, just the ports changed:

### Start Services
```cmd
nssm start GeminiTradeService      # Now on port 4080
nssm start EliteEquityHVService    # Now on port 4013
```

### Check Status
```cmd
nssm status GeminiTradeService
nssm status EliteEquityHVService
```

### Stop Services
```cmd
nssm stop GeminiTradeService
nssm stop EliteEquityHVService
```

---

## ⚠️ Important Notes

### 1. **Restart Required**
If you have the Gemini service currently running on port 8080, you need to:
```cmd
# Stop the current running service
Ctrl+C (in the terminal where it's running)

# Or if running as a service
nssm stop GeminiTradeService

# Then restart with new port
python main.py  # Will now use port 4080
```

### 2. **No Conflicts**
The new ports (4080, 4013) will NOT conflict with:
- ✅ Your existing service on port 8003
- ✅ Any other services running on 8xxx ports

### 3. **Environment Variables**
The services use environment variables for ports:
- `PORT=4080` for Gemini Service
- `EQUITY_HV_PORT=4013` for Elite HV Service

These are automatically set by the NSSM installers.

---

## 🧪 Testing

### Test Gemini Service
```cmd
# After starting the service
curl http://localhost:4080/health

# Or in browser
http://localhost:4080/health
```

### Test Elite HV Service
```cmd
# After starting the service
curl http://localhost:4013/health

# Or in browser
http://localhost:4013/health
```

### Test Google AI Integration
```cmd
cd c:\Users\Dhanasimmaraja\Documents\TradeApp\DTrade\equity_hv_service
python test_google_ai.py
```

The test script will automatically use the new port 4080.

---

## 📋 Quick Reference

### Service Ports
```
Gemini Trade Service:     4080  (was 8080)
Elite Equity HV Service:  4013  (was 8013)
Existing Service:         8003  (unchanged)
```

### URLs
```
Gemini Health:    http://localhost:4080/health
Elite HV Health:  http://localhost:4013/health
Elite HV Dashboard: http://localhost:4013/
```

### Service Names
```
GeminiTradeService
EliteEquityHVService
```

---

## ✅ Next Steps

### 1. Install Services (If Not Already Installed)
```cmd
cd equity_hv_service
manage_services.bat → Press '3'
```

### 2. Start Services
```cmd
manage_services.bat → Press '6'
```

### 3. Verify New Ports
```cmd
manage_services.bat → Press 'S'
```

Should show:
- Gemini Trade Service (Port 4080): RUNNING
- Elite Equity HV Service (Port 4013): RUNNING

### 4. Test Google AI
```cmd
python test_google_ai.py
```

### 5. Check Google AI Usage
```
https://aistudio.google.com/apikey
```

---

## 🎯 Summary

**All port numbers successfully updated to 4xxx series!**

- ✅ No conflicts with existing services
- ✅ All configuration files updated
- ✅ Installation scripts updated
- ✅ Service management unchanged
- ✅ Ready to install and use

**The system is ready for production with the new port configuration!** 🚀

---

*Last Updated: 2025-11-24*  
*Port Series: 4xxx (Updated from 8xxx)*  
*Status: Ready for Installation*
