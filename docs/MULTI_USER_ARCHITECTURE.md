# Multi-User Trading Architecture - Production Implementation

## Overview
This document describes the production-ready architecture for handling multiple users accessing the same trading services.

## Current Architecture (Single User)
```
Frontend → Windows Service (Global State)
           ↓
           Single active/inactive flag
           Single capital pool
```

**Problem:** Multiple users = conflicts

---

## Recommended Architecture: User-Level Virtual Accounts

### System Design

```
┌─────────────────────────────────────────────────────────────┐
│                     Windows Service                          │
│                   (Always Running 24/7)                      │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │           Account Manager Service                   │    │
│  │                                                      │    │
│  │  User Accounts:                                     │    │
│  │  ┌──────────────────────────────────────────────┐  │    │
│  │  │ user_001 (Active)   │ ₹150k │ Scalping      │  │    │
│  │  │ user_002 (Inactive) │ ₹200k │ Hedger        │  │    │
│  │  │ user_003 (Active)   │ ₹100k │ Equity        │  │    │
│  │  └──────────────────────────────────────────────┘  │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌─────────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  AI Scalping    │  │  AI Hedger   │  │ Elite Equity │  │
│  │  Engine         │  │  Engine      │  │  Engine      │  │
│  └─────────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────────┘
         ↑                    ↑                    ↑
    Frontend A          Frontend B          Frontend C
    (User 001)          (User 002)          (User 003)
```

---

## Database Schema

### User Trading Accounts Table
```sql
CREATE TABLE user_trading_accounts (
    user_id TEXT PRIMARY KEY,
    username TEXT NOT NULL,
    email TEXT UNIQUE,
    
    -- Account Status
    is_active BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    
    -- Trading Configuration
    strategy_type TEXT,  -- 'scalping', 'hedger', 'equity', 'all'
    capital REAL NOT NULL,
    max_daily_loss_pct REAL DEFAULT 0.05,
    max_position_size REAL,
    
    -- Risk Management
    daily_pnl REAL DEFAULT 0.0,
    total_pnl REAL DEFAULT 0.0,
    daily_trades_count INTEGER DEFAULT 0,
    max_daily_trades INTEGER DEFAULT 15,
    
    -- Service State
    scalping_active BOOLEAN DEFAULT FALSE,
    hedger_active BOOLEAN DEFAULT FALSE,
    equity_active BOOLEAN DEFAULT FALSE,
    
    -- Authentication
    dhan_client_id TEXT,
    dhan_access_token TEXT,
    token_expires_at TIMESTAMP
);

CREATE INDEX idx_user_active ON user_trading_accounts(is_active);
CREATE INDEX idx_user_strategy ON user_trading_accounts(strategy_type);
```

### User Positions Table
```sql
CREATE TABLE user_positions (
    position_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    strategy_type TEXT,
    
    instrument TEXT NOT NULL,
    side TEXT,  -- 'BUY' or 'SELL'
    quantity INTEGER,
    entry_price REAL,
    current_price REAL,
    
    stop_loss REAL,
    target REAL,
    
    unrealized_pnl REAL,
    status TEXT,  -- 'OPEN', 'CLOSED'
    
    entry_time TIMESTAMP,
    exit_time TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES user_trading_accounts(user_id)
);

CREATE INDEX idx_user_positions ON user_positions(user_id, status);
```

### User Orders Table
```sql
CREATE TABLE user_orders (
    order_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    position_id TEXT,
    
    instrument TEXT,
    side TEXT,
    quantity INTEGER,
    price REAL,
    
    order_type TEXT,  -- 'MARKET', 'LIMIT', 'SL', 'SL-M'
    status TEXT,  -- 'PENDING', 'PLACED', 'EXECUTED', 'CANCELLED', 'REJECTED'
    
    dhan_order_id TEXT,
    exchange_order_id TEXT,
    
    placed_at TIMESTAMP,
    executed_at TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES user_trading_accounts(user_id)
);
```

---

## API Endpoints - Multi-User Support

### Authentication & User Management

#### Register User
```http
POST /api/users/register
Content-Type: application/json

{
  "username": "trader_001",
  "email": "trader@example.com",
  "password": "secure_password",
  "initial_capital": 100000
}

Response:
{
  "success": true,
  "user_id": "user_abc123",
  "message": "Account created successfully"
}
```

#### Login
```http
POST /api/users/login
Content-Type: application/json

{
  "email": "trader@example.com",
  "password": "secure_password"
}

Response:
{
  "success": true,
  "token": "jwt_token_here",
  "user_id": "user_abc123",
  "username": "trader_001"
}
```

### User-Specific Strategy Control

#### Start Strategy (User-Scoped)
```http
POST /api/user/strategies/scalping/start
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "capital": 150000,
  "max_daily_loss": 0.04
}

Response:
{
  "success": true,
  "message": "Scalping strategy activated for your account",
  "user_id": "user_abc123",
  "active": true
}
```

#### Stop Strategy (User-Scoped)
```http
POST /api/user/strategies/scalping/stop
Authorization: Bearer <jwt_token>

Response:
{
  "success": true,
  "message": "Scalping strategy deactivated for your account",
  "active": false
}
```

#### Get User Status
```http
GET /api/user/status
Authorization: Bearer <jwt_token>

Response:
{
  "user_id": "user_abc123",
  "username": "trader_001",
  "capital": 150000,
  "daily_pnl": 2500.00,
  "strategies": {
    "scalping": {
      "active": true,
      "positions": 2,
      "daily_trades": 5,
      "pnl": 1200.00
    },
    "hedger": {
      "active": false
    },
    "equity": {
      "active": true,
      "positions": 3,
      "pnl": 1300.00
    }
  }
}
```

---

## Implementation: Python Service Layer

### User Account Manager
```python
# services/user_account_manager.py

from typing import Dict, Optional
from datetime import datetime
import asyncio

class UserAccount:
    def __init__(self, user_id: str, capital: float):
        self.user_id = user_id
        self.capital = capital
        self.daily_pnl = 0.0
        self.positions = []
        self.is_active = False
        self.strategies = {
            'scalping': {'active': False, 'engine': None},
            'hedger': {'active': False, 'engine': None},
            'equity': {'active': False, 'engine': None}
        }

class MultiUserTradingService:
    def __init__(self):
        self.accounts: Dict[str, UserAccount] = {}
        self.global_engines = {
            'scalping': None,  # Shared engine instance
            'hedger': None,
            'equity': None
        }
        self._lock = asyncio.Lock()
    
    async def register_user(self, user_id: str, capital: float) -> UserAccount:
        """Register a new user account"""
        async with self._lock:
            if user_id in self.accounts:
                raise ValueError(f"User {user_id} already exists")
            
            account = UserAccount(user_id, capital)
            self.accounts[user_id] = account
            
            # Save to database
            await self._save_user_to_db(account)
            
            return account
    
    async def activate_strategy(
        self, 
        user_id: str, 
        strategy: str,
        config: Dict
    ) -> bool:
        """Activate strategy for specific user only"""
        async with self._lock:
            if user_id not in self.accounts:
                raise ValueError(f"User {user_id} not found")
            
            account = self.accounts[user_id]
            
            # Check risk limits
            if not self._check_risk_limits(account):
                raise ValueError("Daily loss limit reached")
            
            # Create user-specific strategy context
            strategy_context = {
                'user_id': user_id,
                'capital': config.get('capital', account.capital),
                'max_loss': config.get('max_daily_loss', 0.05),
                'positions': account.positions
            }
            
            # Activate strategy with user context
            account.strategies[strategy]['active'] = True
            account.strategies[strategy]['config'] = strategy_context
            
            logger.info(f"Strategy {strategy} activated for user {user_id}")
            return True
    
    async def deactivate_strategy(
        self, 
        user_id: str, 
        strategy: str
    ) -> bool:
        """Deactivate strategy for specific user"""
        async with self._lock:
            if user_id not in self.accounts:
                raise ValueError(f"User {user_id} not found")
            
            account = self.accounts[user_id]
            account.strategies[strategy]['active'] = False
            
            # Close user's positions in this strategy
            await self._close_user_positions(user_id, strategy)
            
            logger.info(f"Strategy {strategy} deactivated for user {user_id}")
            return True
    
    def _check_risk_limits(self, account: UserAccount) -> bool:
        """Check if user has exceeded risk limits"""
        max_loss = account.capital * 0.05  # 5% max loss
        return account.daily_pnl > -max_loss
    
    async def _close_user_positions(self, user_id: str, strategy: str):
        """Close all positions for user in specific strategy"""
        account = self.accounts[user_id]
        positions_to_close = [
            p for p in account.positions 
            if p['strategy'] == strategy and p['status'] == 'OPEN'
        ]
        
        for position in positions_to_close:
            await self._execute_exit(user_id, position)
    
    def get_user_status(self, user_id: str) -> Dict:
        """Get comprehensive status for user"""
        if user_id not in self.accounts:
            raise ValueError(f"User {user_id} not found")
        
        account = self.accounts[user_id]
        
        return {
            'user_id': user_id,
            'capital': account.capital,
            'daily_pnl': account.daily_pnl,
            'strategies': {
                name: {
                    'active': strategy['active'],
                    'positions': len([p for p in account.positions if p['strategy'] == name])
                }
                for name, strategy in account.strategies.items()
            },
            'positions': account.positions
        }

# Global instance
user_service = MultiUserTradingService()
```

---

## Frontend Authentication Flow

### Login Component
```typescript
// src/services/auth.ts

export interface User {
  user_id: string;
  username: string;
  email: string;
  token: string;
}

export class AuthService {
  private static TOKEN_KEY = 'dtrade_auth_token';
  private static USER_KEY = 'dtrade_user';

  static async login(email: string, password: string): Promise<User> {
    const response = await fetch('http://localhost:4000/api/users/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });

    if (!response.ok) {
      throw new Error('Login failed');
    }

    const data = await response.json();
    
    // Store token and user info
    localStorage.setItem(this.TOKEN_KEY, data.token);
    localStorage.setItem(this.USER_KEY, JSON.stringify(data));
    
    return data;
  }

  static getAuthHeader(): Record<string, string> {
    const token = localStorage.getItem(this.TOKEN_KEY);
    return token ? { 'Authorization': `Bearer ${token}` } : {};
  }

  static getCurrentUser(): User | null {
    const userStr = localStorage.getItem(this.USER_KEY);
    return userStr ? JSON.parse(userStr) : null;
  }

  static logout(): void {
    localStorage.removeItem(this.TOKEN_KEY);
    localStorage.removeItem(this.USER_KEY);
  }
}
```

### Updated Strategy Service
```typescript
// src/services/strategies.ts

export class UserStrategyService {
  private baseUrl = 'http://localhost:4000/api/user/strategies';

  async startStrategy(
    strategy: 'scalping' | 'hedger' | 'equity',
    config: { capital: number; max_daily_loss: number }
  ) {
    const response = await fetch(`${this.baseUrl}/${strategy}/start`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...AuthService.getAuthHeader()
      },
      body: JSON.stringify(config)
    });

    if (!response.ok) {
      throw new Error('Failed to start strategy');
    }

    return response.json();
  }

  async stopStrategy(strategy: 'scalping' | 'hedger' | 'equity') {
    const response = await fetch(`${this.baseUrl}/${strategy}/stop`, {
      method: 'POST',
      headers: AuthService.getAuthHeader()
    });

    if (!response.ok) {
      throw new Error('Failed to stop strategy');
    }

    return response.json();
  }

  async getUserStatus() {
    const response = await fetch('http://localhost:4000/api/user/status', {
      headers: AuthService.getAuthHeader()
    });

    if (!response.ok) {
      throw new Error('Failed to get status');
    }

    return response.json();
  }
}
```

---

## Benefits of This Architecture

### ✅ Isolation
- Each user has their own virtual trading account
- One user's actions don't affect others
- Separate capital, positions, and P&L

### ✅ Scalability
- Add unlimited users without infrastructure changes
- Windows service runs continuously
- No service restarts needed

### ✅ Risk Management
- Per-user capital limits
- Per-user daily loss limits
- User can't exceed their allocated capital

### ✅ Audit Trail
- Every order tied to specific user
- Full transaction history per user
- Compliance-ready logging

### ✅ Real-Time
- All users see real-time updates
- No polling needed
- WebSocket support for live data

---

## Alternative: Admin-Only Control (Simpler)

If you prefer **centralized control**:

```typescript
// Only admins can start/stop services
const hasAdminRole = currentUser.role === 'admin';

<button 
  onClick={toggleStrategy}
  disabled={!hasAdminRole}
>
  {hasAdminRole ? 'Toggle Strategy' : 'Admin Only'}
</button>

// Regular users see status but cannot control
<div className="strategy-status">
  <StatusIndicator active={strategyActive} />
  <span>Strategy is {strategyActive ? 'Active' : 'Inactive'}</span>
  {!hasAdminRole && (
    <p className="text-gray-400 text-sm">
      Contact admin to change strategy status
    </p>
  )}
</div>
```

---

## Recommendation Summary

**For Your Use Case (Individual Trader, Multiple Instances):**
- Use **User-Level Virtual Accounts**
- Windows service runs 24/7
- Each user controls only their own account
- No conflicts between users
- Easy to implement with current architecture

**Next Steps:**
1. Add user authentication (JWT tokens)
2. Create user accounts table in database
3. Modify services to accept user_id parameter
4. Update frontend to pass authentication headers
5. Test with multiple concurrent users

Would you like me to implement the user account management system?
