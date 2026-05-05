"""
WebSocket connection manager for real-time data streaming
"""

import json
import logging
from typing import Dict, List, Optional, Set
from datetime import datetime

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time data streaming"""
    
    def __init__(self):
        # Store active connections
        self.active_connections: Dict[str, WebSocket] = {}
        
        # Store subscriptions for each client
        self.client_subscriptions: Dict[str, Set[str]] = {}
        
        # Store connection metadata
        self.connection_metadata: Dict[str, dict] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        """Accept new WebSocket connection"""
        try:
            await websocket.accept()
            
            self.active_connections[client_id] = websocket
            self.client_subscriptions[client_id] = set()
            self.connection_metadata[client_id] = {
                "connected_at": datetime.now().isoformat(),
                "last_activity": datetime.now().isoformat(),
                "message_count": 0
            }
            
            logger.info(f"✅ WebSocket client {client_id} connected")
            
            # Send welcome message
            await self.send_personal_message({
                "type": "connection",
                "status": "connected",
                "client_id": client_id,
                "timestamp": datetime.now().isoformat()
            }, client_id)
            
        except Exception as e:
            logger.error(f"❌ Error connecting WebSocket client {client_id}: {e}")
            raise
    
    def disconnect(self, client_id: str):
        """Remove WebSocket connection"""
        try:
            if client_id in self.active_connections:
                del self.active_connections[client_id]
            
            if client_id in self.client_subscriptions:
                del self.client_subscriptions[client_id]
            
            if client_id in self.connection_metadata:
                del self.connection_metadata[client_id]
            
            logger.info(f"🔌 WebSocket client {client_id} disconnected")
            
        except Exception as e:
            logger.error(f"❌ Error disconnecting WebSocket client {client_id}: {e}")
    
    async def send_personal_message(self, message: dict, client_id: str):
        """Send message to specific client"""
        try:
            if client_id in self.active_connections:
                websocket = self.active_connections[client_id]
                await websocket.send_text(json.dumps(message))
                
                # Update metadata
                if client_id in self.connection_metadata:
                    self.connection_metadata[client_id]["last_activity"] = datetime.now().isoformat()
                    self.connection_metadata[client_id]["message_count"] += 1
                
        except WebSocketDisconnect:
            logger.info(f"Client {client_id} disconnected during message send")
            self.disconnect(client_id)
        except Exception as e:
            logger.error(f"❌ Error sending message to {client_id}: {e}")
            self.disconnect(client_id)
    
    async def broadcast(self, message: dict, exclude_clients: Optional[List[str]] = None):
        """Broadcast message to all connected clients"""
        exclude_clients = exclude_clients or []
        
        disconnected_clients = []
        
        for client_id, websocket in self.active_connections.items():
            if client_id not in exclude_clients:
                try:
                    await websocket.send_text(json.dumps(message))
                    
                    # Update metadata
                    if client_id in self.connection_metadata:
                        self.connection_metadata[client_id]["last_activity"] = datetime.now().isoformat()
                        self.connection_metadata[client_id]["message_count"] += 1
                        
                except WebSocketDisconnect:
                    disconnected_clients.append(client_id)
                except Exception as e:
                    logger.error(f"❌ Error broadcasting to {client_id}: {e}")
                    disconnected_clients.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected_clients:
            self.disconnect(client_id)
    
    async def broadcast_to_subscribed(self, message: dict, subscription_type: str):
        """Broadcast to clients subscribed to specific data type"""
        disconnected_clients = []
        
        for client_id, subscriptions in self.client_subscriptions.items():
            if subscription_type in subscriptions:
                try:
                    websocket = self.active_connections[client_id]
                    await websocket.send_text(json.dumps(message))
                    
                    # Update metadata
                    if client_id in self.connection_metadata:
                        self.connection_metadata[client_id]["last_activity"] = datetime.now().isoformat()
                        self.connection_metadata[client_id]["message_count"] += 1
                        
                except WebSocketDisconnect:
                    disconnected_clients.append(client_id)
                except Exception as e:
                    logger.error(f"❌ Error broadcasting to subscribed client {client_id}: {e}")
                    disconnected_clients.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected_clients:
            self.disconnect(client_id)
    
    async def handle_message(self, client_id: str, data: str):
        """Handle incoming WebSocket message"""
        try:
            message = json.loads(data)
            message_type = message.get("type")
            
            if message_type == "subscribe":
                await self.handle_subscription(client_id, message)
            elif message_type == "unsubscribe":
                await self.handle_unsubscription(client_id, message)
            elif message_type == "ping":
                await self.handle_ping(client_id)
            else:
                logger.warning(f"Unknown message type: {message_type}")
                
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON from client {client_id}: {data}")
        except Exception as e:
            logger.error(f"Error handling message from {client_id}: {e}")
    
    async def handle_subscription(self, client_id: str, message: dict):
        """Handle subscription request"""
        try:
            subscription_types = message.get("subscriptions", [])
            
            if client_id not in self.client_subscriptions:
                self.client_subscriptions[client_id] = set()
            
            for sub_type in subscription_types:
                self.client_subscriptions[client_id].add(sub_type)
            
            logger.info(f"Client {client_id} subscribed to: {subscription_types}")
            
            # Send confirmation
            await self.send_personal_message({
                "type": "subscription_confirmed",
                "subscriptions": list(self.client_subscriptions[client_id]),
                "timestamp": datetime.now().isoformat()
            }, client_id)
            
        except Exception as e:
            logger.error(f"Error handling subscription for {client_id}: {e}")
    
    async def handle_unsubscription(self, client_id: str, message: dict):
        """Handle unsubscription request"""
        try:
            subscription_types = message.get("subscriptions", [])
            
            if client_id in self.client_subscriptions:
                for sub_type in subscription_types:
                    self.client_subscriptions[client_id].discard(sub_type)
            
            logger.info(f"Client {client_id} unsubscribed from: {subscription_types}")
            
            # Send confirmation
            await self.send_personal_message({
                "type": "unsubscription_confirmed",
                "unsubscribed": subscription_types,
                "remaining_subscriptions": list(self.client_subscriptions.get(client_id, [])),
                "timestamp": datetime.now().isoformat()
            }, client_id)
            
        except Exception as e:
            logger.error(f"Error handling unsubscription for {client_id}: {e}")
    
    async def handle_ping(self, client_id: str):
        """Handle ping message"""
        try:
            await self.send_personal_message({
                "type": "pong",
                "timestamp": datetime.now().isoformat()
            }, client_id)
            
        except Exception as e:
            logger.error(f"Error handling ping from {client_id}: {e}")
    
    def get_connection_count(self) -> int:
        """Get number of active connections"""
        return len(self.active_connections)
    
    def get_client_info(self, client_id: str) -> Optional[dict]:
        """Get client connection information"""
        if client_id in self.connection_metadata:
            info = self.connection_metadata[client_id].copy()
            info["subscriptions"] = list(self.client_subscriptions.get(client_id, []))
            info["is_connected"] = client_id in self.active_connections
            return info
        return None
    
    def get_all_clients_info(self) -> Dict[str, dict]:
        """Get information about all connected clients"""
        return {
            client_id: self.get_client_info(client_id)
            for client_id in self.active_connections.keys()
        }
    
    async def send_market_data(self, data: dict):
        """Send market data to subscribed clients"""
        await self.broadcast_to_subscribed({
            "type": "market_data",
            "data": data,
            "timestamp": datetime.now().isoformat()
        }, "market_data")
    
    async def send_order_update(self, order_data: dict):
        """Send order update to clients"""
        await self.broadcast({
            "type": "order_update",
            "data": order_data,
            "timestamp": datetime.now().isoformat()
        })
    
    async def send_trade_signal(self, signal_data: dict):
        """Send AI trade signal to subscribed clients"""
        await self.broadcast_to_subscribed({
            "type": "trade_signal",
            "data": signal_data,
            "timestamp": datetime.now().isoformat()
        }, "trade_signals")
    
    async def send_portfolio_update(self, portfolio_data: dict):
        """Send portfolio update to clients"""
        await self.broadcast({
            "type": "portfolio_update",
            "data": portfolio_data,
            "timestamp": datetime.now().isoformat()
        })
    
    async def send_system_alert(self, alert: dict, severity: str = "info"):
        """Send system alert to all clients"""
        await self.broadcast({
            "type": "system_alert",
            "severity": severity,
            "alert": alert,
            "timestamp": datetime.now().isoformat()
        })


# Create global WebSocket manager instance
websocket_manager = ConnectionManager()
