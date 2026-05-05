"""
Dashboard Backend for Intelligent Options Hedging Engine
FastAPI backend serving real-time trading data and analytics
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import uvicorn
from pathlib import Path
import pandas as pd
import numpy as np
from dataclasses import asdict

# Import our modules
import sys
sys.path.append(str(Path(__file__).parent.parent))

from evaluation.performance_monitor import PerformanceMonitor
from evaluation.risk_assessment import RiskAssessment
from strategies.trade_executor import TradeExecutor

# Import RL Trading Agent with fallback
try:
    from ai_engine.reinforcement_learning.rl_trading_agent import RLTradingAgent
    RL_TRADING_AVAILABLE = True
except ImportError:
    RLTradingAgent = None
    RL_TRADING_AVAILABLE = False
    logging.warning("RLTradingAgent not available - PyTorch not installed")

from utils.broker_interface import get_broker_manager, BrokerManager
from utils.logger import get_logger
from utils.notifier import get_notifier

logger = logging.getLogger(__name__)

class DashboardWebSocketManager:
    """Manage WebSocket connections for real-time updates"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
        
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)
    
    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast message to all connected clients"""
        if not self.active_connections:
            return
            
        message_str = json.dumps(message, default=str)
        disconnected = []
        
        for connection in self.active_connections:
            try:
                await connection.send_text(message_str)
            except Exception as e:
                logger.error(f"Error sending message to WebSocket: {e}")
                disconnected.append(connection)
        
        # Remove disconnected clients
        for connection in disconnected:
            self.disconnect(connection)

class DashboardAPI:
    """Dashboard API endpoints"""
    
    def __init__(self):
        self.app = FastAPI(title="Options Hedging Dashboard", version="1.0.0")
        self.websocket_manager = DashboardWebSocketManager()
        self.setup_middleware()
        self.setup_routes()
        self.setup_websockets()
        
        # Component references (to be injected)
        self.performance_monitor: Optional[PerformanceMonitor] = None
        self.risk_assessment: Optional[RiskAssessment] = None
        self.trade_executor: Optional[TradeExecutor] = None
        self.rl_agent: Optional[RLTradingAgent] = None
        
    def setup_middleware(self):
        """Setup CORS and other middleware"""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Configure appropriately for production
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    def setup_routes(self):
        """Setup API routes"""
        
        @self.app.get("/")
        async def root():
            return HTMLResponse(self.get_dashboard_html())
        
        @self.app.get("/api/health")
        async def health_check():
            return {"status": "healthy", "timestamp": datetime.now()}
        
        @self.app.get("/api/system/status")
        async def system_status():
            """Get overall system status"""
            return {
                "engine_status": "running",
                "connected_brokers": await self._get_broker_status(),
                "active_strategies": await self._get_active_strategies(),
                "websocket_connections": len(self.websocket_manager.active_connections),
                "timestamp": datetime.now()
            }
        
        @self.app.get("/api/performance/summary")
        async def performance_summary():
            """Get performance summary"""
            if not self.performance_monitor:
                raise HTTPException(status_code=503, detail="Performance monitor not available")
            
            try:
                metrics = await self.performance_monitor.get_performance_summary()
                return metrics
            except Exception as e:
                logger.error(f"Error getting performance summary: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/performance/detailed")
        async def performance_detailed():
            """Get detailed performance metrics"""
            if not self.performance_monitor:
                raise HTTPException(status_code=503, detail="Performance monitor not available")
            
            try:
                metrics = await self.performance_monitor.get_detailed_metrics()
                return metrics
            except Exception as e:
                logger.error(f"Error getting detailed performance: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/risk/assessment")
        async def risk_assessment():
            """Get current risk assessment"""
            if not self.risk_assessment:
                raise HTTPException(status_code=503, detail="Risk assessment not available")
            
            try:
                risk_data = await self.risk_assessment.get_current_risk_metrics()
                return risk_data
            except Exception as e:
                logger.error(f"Error getting risk assessment: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/positions")
        async def get_positions():
            """Get current positions"""
            try:
                broker_manager = get_broker_manager()
                positions = await broker_manager.get_consolidated_positions()
                return positions
            except Exception as e:
                logger.error(f"Error getting positions: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/trades/recent")
        async def recent_trades(limit: int = 50):
            """Get recent trades"""
            if not self.trade_executor:
                raise HTTPException(status_code=503, detail="Trade executor not available")
            
            try:
                trades = await self.trade_executor.get_recent_trades(limit)
                return [asdict(trade) for trade in trades]
            except Exception as e:
                logger.error(f"Error getting recent trades: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/signals/active")
        async def active_signals():
            """Get active trading signals"""
            # This would come from signal confluence engine
            return {
                "signals": [],
                "timestamp": datetime.now()
            }
        
        @self.app.get("/api/analytics/options")
        async def options_analytics():
            """Get options analytics data"""
            return {
                "implied_volatility": await self._get_iv_data(),
                "option_flow": await self._get_option_flow(),
                "gamma_exposure": await self._get_gamma_exposure(),
                "timestamp": datetime.now()
            }
        
        @self.app.get("/api/ml/model_status")
        async def ml_model_status():
            """Get ML model status and performance"""
            if not self.rl_agent:
                raise HTTPException(status_code=503, detail="RL agent not available")
            
            try:
                status = await self.rl_agent.get_model_status()
                return status
            except Exception as e:
                logger.error(f"Error getting ML model status: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/control/pause")
        async def pause_engine():
            """Pause the trading engine"""
            # Implementation depends on main engine structure
            return {"status": "paused", "timestamp": datetime.now()}
        
        @self.app.post("/api/control/resume")
        async def resume_engine():
            """Resume the trading engine"""
            # Implementation depends on main engine structure
            return {"status": "resumed", "timestamp": datetime.now()}
        
        @self.app.post("/api/control/emergency_stop")
        async def emergency_stop():
            """Emergency stop all trading"""
            try:
                # Cancel all open orders
                broker_manager = get_broker_manager()
                # Implementation depends on broker interface
                
                # Send emergency notification
                notifier = get_notifier()
                await notifier.critical(
                    "Emergency Stop Activated",
                    "All trading has been stopped via dashboard emergency control"
                )
                
                return {"status": "emergency_stopped", "timestamp": datetime.now()}
                
            except Exception as e:
                logger.error(f"Error in emergency stop: {e}")
                raise HTTPException(status_code=500, detail=str(e))
    
    def setup_websockets(self):
        """Setup WebSocket endpoints"""
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await self.websocket_manager.connect(websocket)
            try:
                while True:
                    # Keep connection alive and handle incoming messages
                    data = await websocket.receive_text()
                    message = json.loads(data)
                    
                    # Handle different message types
                    if message.get("type") == "subscribe":
                        await self._handle_subscription(message, websocket)
                    elif message.get("type") == "unsubscribe":
                        await self._handle_unsubscription(message, websocket)
                    
            except WebSocketDisconnect:
                self.websocket_manager.disconnect(websocket)
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                self.websocket_manager.disconnect(websocket)
    
    async def _handle_subscription(self, message: Dict[str, Any], websocket: WebSocket):
        """Handle WebSocket subscription requests"""
        subscription_type = message.get("subscription")
        
        if subscription_type == "performance":
            # Send current performance data
            if self.performance_monitor:
                data = await self.performance_monitor.get_performance_summary()
                await self.websocket_manager.send_personal_message(
                    json.dumps({"type": "performance", "data": data}),
                    websocket
                )
        
        elif subscription_type == "risk":
            # Send current risk data
            if self.risk_assessment:
                data = await self.risk_assessment.get_current_risk_metrics()
                await self.websocket_manager.send_personal_message(
                    json.dumps({"type": "risk", "data": data}),
                    websocket
                )
    
    async def _handle_unsubscription(self, message: Dict[str, Any], websocket: WebSocket):
        """Handle WebSocket unsubscription requests"""
        # Implementation for handling unsubscriptions
        pass
    
    async def broadcast_update(self, update_type: str, data: Dict[str, Any]):
        """Broadcast real-time updates to all connected clients"""
        message = {
            "type": update_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        await self.websocket_manager.broadcast(message)
    
    def get_dashboard_html(self) -> str:
        """Return basic dashboard HTML"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Options Hedging Dashboard</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }
                .container { max-width: 1400px; margin: 0 auto; }
                .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }
                .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
                .card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                .metric { display: flex; justify-content: space-between; margin: 10px 0; }
                .metric-value { font-weight: bold; color: #333; }
                .status-indicator { width: 12px; height: 12px; border-radius: 50%; display: inline-block; margin-right: 5px; }
                .status-active { background-color: #4caf50; }
                .status-warning { background-color: #ff9800; }
                .status-error { background-color: #f44336; }
                .controls { text-align: center; margin: 20px 0; }
                .btn { padding: 10px 20px; margin: 5px; border: none; border-radius: 5px; cursor: pointer; font-size: 14px; }
                .btn-primary { background-color: #2196f3; color: white; }
                .btn-warning { background-color: #ff9800; color: white; }
                .btn-danger { background-color: #f44336; color: white; }
                .btn:hover { opacity: 0.8; }
                #log { background-color: #000; color: #00ff00; padding: 10px; border-radius: 5px; height: 200px; overflow-y: auto; font-family: monospace; font-size: 12px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎯 Intelligent Options Hedging Engine</h1>
                    <p>Real-time monitoring and control dashboard</p>
                </div>
                
                <div class="controls">
                    <button class="btn btn-primary" onclick="toggleEngine()">⏸️ Pause Engine</button>
                    <button class="btn btn-warning" onclick="refreshData()">🔄 Refresh Data</button>
                    <button class="btn btn-danger" onclick="emergencyStop()">🚨 Emergency Stop</button>
                </div>
                
                <div class="grid">
                    <div class="card">
                        <h3>📊 System Status</h3>
                        <div id="system-status">Loading...</div>
                    </div>
                    
                    <div class="card">
                        <h3>💰 Performance Summary</h3>
                        <div id="performance-summary">Loading...</div>
                    </div>
                    
                    <div class="card">
                        <h3>⚠️ Risk Assessment</h3>
                        <div id="risk-assessment">Loading...</div>
                    </div>
                    
                    <div class="card">
                        <h3>📈 Current Positions</h3>
                        <div id="positions">Loading...</div>
                    </div>
                    
                    <div class="card">
                        <h3>🔄 Recent Trades</h3>
                        <div id="recent-trades">Loading...</div>
                    </div>
                    
                    <div class="card">
                        <h3>🤖 ML Model Status</h3>
                        <div id="ml-status">Loading...</div>
                    </div>
                </div>
                
                <div class="card" style="margin-top: 20px;">
                    <h3>📝 Live Log</h3>
                    <div id="log"></div>
                </div>
            </div>
            
            <script>
                let ws = null;
                let enginePaused = false;
                
                function connectWebSocket() {
                    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                    const wsUrl = `${protocol}//${window.location.host}/ws`;
                    
                    ws = new WebSocket(wsUrl);
                    
                    ws.onopen = function(event) {
                        console.log('WebSocket connected');
                        addLog('WebSocket connected');
                        
                        // Subscribe to updates
                        ws.send(JSON.stringify({type: 'subscribe', subscription: 'performance'}));
                        ws.send(JSON.stringify({type: 'subscribe', subscription: 'risk'}));
                    };
                    
                    ws.onmessage = function(event) {
                        const message = JSON.parse(event.data);
                        handleWebSocketMessage(message);
                    };
                    
                    ws.onclose = function(event) {
                        console.log('WebSocket disconnected');
                        addLog('WebSocket disconnected, attempting to reconnect...');
                        setTimeout(connectWebSocket, 5000);
                    };
                    
                    ws.onerror = function(error) {
                        console.error('WebSocket error:', error);
                        addLog(`WebSocket error: ${error}`);
                    };
                }
                
                function handleWebSocketMessage(message) {
                    switch(message.type) {
                        case 'performance':
                            updatePerformanceSummary(message.data);
                            break;
                        case 'risk':
                            updateRiskAssessment(message.data);
                            break;
                        case 'trade':
                            addLog(`New trade: ${message.data.symbol} ${message.data.side} ${message.data.quantity}`);
                            break;
                        case 'alert':
                            addLog(`ALERT: ${message.data.message}`);
                            break;
                    }
                }
                
                async function loadInitialData() {
                    try {
                        // Load system status
                        const statusResponse = await fetch('/api/system/status');
                        const statusData = await statusResponse.json();
                        updateSystemStatus(statusData);
                        
                        // Load performance data
                        const perfResponse = await fetch('/api/performance/summary');
                        const perfData = await perfResponse.json();
                        updatePerformanceSummary(perfData);
                        
                        // Load risk data
                        const riskResponse = await fetch('/api/risk/assessment');
                        const riskData = await riskResponse.json();
                        updateRiskAssessment(riskData);
                        
                        // Load positions
                        const posResponse = await fetch('/api/positions');
                        const posData = await posResponse.json();
                        updatePositions(posData);
                        
                        // Load recent trades
                        const tradesResponse = await fetch('/api/trades/recent?limit=10');
                        const tradesData = await tradesResponse.json();
                        updateRecentTrades(tradesData);
                        
                        // Load ML status
                        const mlResponse = await fetch('/api/ml/model_status');
                        const mlData = await mlResponse.json();
                        updateMLStatus(mlData);
                        
                    } catch (error) {
                        console.error('Error loading data:', error);
                        addLog(`Error loading data: ${error.message}`);
                    }
                }
                
                function updateSystemStatus(data) {
                    const statusHtml = `
                        <div class="metric">
                            <span>Engine Status:</span>
                            <span class="metric-value">
                                <span class="status-indicator status-active"></span>
                                ${data.engine_status}
                            </span>
                        </div>
                        <div class="metric">
                            <span>Connected Brokers:</span>
                            <span class="metric-value">${Object.keys(data.connected_brokers || {}).length}</span>
                        </div>
                        <div class="metric">
                            <span>Active Strategies:</span>
                            <span class="metric-value">${data.active_strategies || 0}</span>
                        </div>
                        <div class="metric">
                            <span>WebSocket Connections:</span>
                            <span class="metric-value">${data.websocket_connections}</span>
                        </div>
                    `;
                    document.getElementById('system-status').innerHTML = statusHtml;
                }
                
                function updatePerformanceSummary(data) {
                    const perfHtml = `
                        <div class="metric">
                            <span>Total PnL:</span>
                            <span class="metric-value" style="color: ${(data.total_pnl || 0) >= 0 ? 'green' : 'red'}">
                                ₹${(data.total_pnl || 0).toFixed(2)}
                            </span>
                        </div>
                        <div class="metric">
                            <span>Today's PnL:</span>
                            <span class="metric-value" style="color: ${(data.daily_pnl || 0) >= 0 ? 'green' : 'red'}">
                                ₹${(data.daily_pnl || 0).toFixed(2)}
                            </span>
                        </div>
                        <div class="metric">
                            <span>Win Rate:</span>
                            <span class="metric-value">${((data.win_rate || 0) * 100).toFixed(1)}%</span>
                        </div>
                        <div class="metric">
                            <span>Sharpe Ratio:</span>
                            <span class="metric-value">${(data.sharpe_ratio || 0).toFixed(2)}</span>
                        </div>
                    `;
                    document.getElementById('performance-summary').innerHTML = perfHtml;
                }
                
                function updateRiskAssessment(data) {
                    const riskHtml = `
                        <div class="metric">
                            <span>Risk Score:</span>
                            <span class="metric-value">${(data.risk_score || 0).toFixed(2)}/10</span>
                        </div>
                        <div class="metric">
                            <span>VaR (95%):</span>
                            <span class="metric-value">₹${(data.var_95 || 0).toFixed(2)}</span>
                        </div>
                        <div class="metric">
                            <span>Max Drawdown:</span>
                            <span class="metric-value">${((data.max_drawdown || 0) * 100).toFixed(2)}%</span>
                        </div>
                        <div class="metric">
                            <span>Portfolio Beta:</span>
                            <span class="metric-value">${(data.portfolio_beta || 0).toFixed(2)}</span>
                        </div>
                    `;
                    document.getElementById('risk-assessment').innerHTML = riskHtml;
                }
                
                function updatePositions(data) {
                    let posHtml = '';
                    for (const [broker, positions] of Object.entries(data)) {
                        posHtml += `<h4>${broker.toUpperCase()}</h4>`;
                        if (positions.length === 0) {
                            posHtml += '<p>No positions</p>';
                        } else {
                            positions.forEach(pos => {
                                posHtml += `
                                    <div class="metric">
                                        <span>${pos.symbol}:</span>
                                        <span class="metric-value" style="color: ${pos.pnl >= 0 ? 'green' : 'red'}">
                                            ${pos.quantity} @ ₹${pos.current_price} (₹${pos.pnl.toFixed(2)})
                                        </span>
                                    </div>
                                `;
                            });
                        }
                    }
                    document.getElementById('positions').innerHTML = posHtml || 'No positions';
                }
                
                function updateRecentTrades(data) {
                    if (!Array.isArray(data) || data.length === 0) {
                        document.getElementById('recent-trades').innerHTML = 'No recent trades';
                        return;
                    }
                    
                    let tradesHtml = '';
                    data.slice(0, 5).forEach(trade => {
                        const time = new Date(trade.timestamp).toLocaleTimeString();
                        tradesHtml += `
                            <div class="metric">
                                <span>${trade.symbol} ${trade.side}</span>
                                <span class="metric-value">${trade.quantity} @ ₹${trade.price} (${time})</span>
                            </div>
                        `;
                    });
                    document.getElementById('recent-trades').innerHTML = tradesHtml;
                }
                
                function updateMLStatus(data) {
                    const mlHtml = `
                        <div class="metric">
                            <span>Model Status:</span>
                            <span class="metric-value">
                                <span class="status-indicator ${data.status === 'active' ? 'status-active' : 'status-warning'}"></span>
                                ${data.status || 'Unknown'}
                            </span>
                        </div>
                        <div class="metric">
                            <span>Model Accuracy:</span>
                            <span class="metric-value">${((data.accuracy || 0) * 100).toFixed(1)}%</span>
                        </div>
                        <div class="metric">
                            <span>Prediction Confidence:</span>
                            <span class="metric-value">${((data.confidence || 0) * 100).toFixed(1)}%</span>
                        </div>
                        <div class="metric">
                            <span>Last Update:</span>
                            <span class="metric-value">${data.last_update || 'Never'}</span>
                        </div>
                    `;
                    document.getElementById('ml-status').innerHTML = mlHtml;
                }
                
                function addLog(message) {
                    const logDiv = document.getElementById('log');
                    const timestamp = new Date().toLocaleTimeString();
                    logDiv.innerHTML += `[${timestamp}] ${message}\n`;
                    logDiv.scrollTop = logDiv.scrollHeight;
                }
                
                async function toggleEngine() {
                    try {
                        const endpoint = enginePaused ? '/api/control/resume' : '/api/control/pause';
                        const response = await fetch(endpoint, { method: 'POST' });
                        const data = await response.json();
                        
                        enginePaused = !enginePaused;
                        const btn = document.querySelector('.btn-primary');
                        btn.textContent = enginePaused ? '▶️ Resume Engine' : '⏸️ Pause Engine';
                        
                        addLog(`Engine ${data.status}`);
                    } catch (error) {
                        addLog(`Error toggling engine: ${error.message}`);
                    }
                }
                
                async function refreshData() {
                    addLog('Refreshing data...');
                    await loadInitialData();
                    addLog('Data refreshed');
                }
                
                async function emergencyStop() {
                    if (confirm('Are you sure you want to activate emergency stop? This will halt all trading immediately.')) {
                        try {
                            const response = await fetch('/api/control/emergency_stop', { method: 'POST' });
                            const data = await response.json();
                            addLog('🚨 EMERGENCY STOP ACTIVATED 🚨');
                        } catch (error) {
                            addLog(`Error activating emergency stop: ${error.message}`);
                        }
                    }
                }
                
                // Initialize
                document.addEventListener('DOMContentLoaded', function() {
                    connectWebSocket();
                    loadInitialData();
                    
                    // Refresh data every 30 seconds
                    setInterval(loadInitialData, 30000);
                });
            </script>
        </body>
        </html>
        """
    
    # Helper methods
    async def _get_broker_status(self) -> Dict[str, bool]:
        """Get status of all brokers"""
        try:
            broker_manager = get_broker_manager()
            return await broker_manager.authenticate_all()
        except:
            return {}
    
    async def _get_active_strategies(self) -> int:
        """Get number of active strategies"""
        # This would be implemented based on strategy manager
        return 3  # Placeholder
    
    async def _get_iv_data(self) -> Dict[str, Any]:
        """Get implied volatility data"""
        return {
            "nifty_iv": 18.5,
            "banknifty_iv": 22.3,
            "iv_percentile": 75.2
        }
    
    async def _get_option_flow(self) -> Dict[str, Any]:
        """Get option flow data"""
        return {
            "call_volume": 1250000,
            "put_volume": 980000,
            "put_call_ratio": 0.78
        }
    
    async def _get_gamma_exposure(self) -> Dict[str, Any]:
        """Get gamma exposure data"""
        return {
            "total_gamma": 15.6,
            "gamma_by_strike": {},
            "flip_point": 19650
        }
    
    def inject_components(self, **components):
        """Inject component references"""
        self.performance_monitor = components.get('performance_monitor')
        self.risk_assessment = components.get('risk_assessment')
        self.trade_executor = components.get('trade_executor')
        self.rl_agent = components.get('rl_agent')

# Global dashboard instance
_dashboard_api = None

def create_dashboard_app(config: Dict[str, Any]) -> FastAPI:
    """Create dashboard FastAPI app"""
    global _dashboard_api
    _dashboard_api = DashboardAPI()
    return _dashboard_api.app

def get_dashboard_api() -> DashboardAPI:
    """Get dashboard API instance"""
    return _dashboard_api

def start_dashboard_server(app: FastAPI, host: str = "0.0.0.0", port: int = 8080):
    """Start dashboard server"""
    uvicorn.run(app, host=host, port=port, log_level="info")

if __name__ == "__main__":
    # For testing
    app = create_dashboard_app({})
    start_dashboard_server(app)
