"""
REST API for the trading system
"""
import os
import logging
from flask import Flask, request, jsonify
import threading
import json
from datetime import datetime
from dotenv import load_dotenv

# Load main trading system
from main import TradingSystem

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("api_server.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize trading system
trading_system = TradingSystem(initial_capital=1000000)  # 10 Lakhs
system_thread = None

@app.route('/api/system/start', methods=['POST'])
def start_system():
    """Start the trading system"""
    global system_thread
    
    try:
        if system_thread and system_thread.is_alive():
            return jsonify({'success': False, 'message': 'Trading system already running'})
        
        # Start in a separate thread
        system_thread = threading.Thread(target=trading_system.start)
        system_thread.daemon = True
        system_thread.start()
        
        return jsonify({'success': True, 'message': 'Trading system starting'})
    
    except Exception as e:
        logger.error(f"Error starting system: {e}", exc_info=True)
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/api/system/stop', methods=['POST'])
def stop_system():
    """Stop the trading system"""
    try:
        if not system_thread or not system_thread.is_alive():
            return jsonify({'success': False, 'message': 'Trading system not running'})
        
        trading_system.stop()
        system_thread.join(timeout=10)
        
        return jsonify({'success': True, 'message': 'Trading system stopped'})
    
    except Exception as e:
        logger.error(f"Error stopping system: {e}", exc_info=True)
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/api/system/status', methods=['GET'])
def system_status():
    """Get trading system status"""
    try:
        status = {
            'running': system_thread is not None and system_thread.is_alive(),
            'market_open': trading_system.is_market_open,
            'current_capital': trading_system.current_capital,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Add position info if available
        if hasattr(trading_system, 'position_manager'):
            positions = trading_system.position_manager.get_all_positions()
            status['open_positions'] = len(positions)
        
        return jsonify(status)
    
    except Exception as e:
        logger.error(f"Error getting status: {e}", exc_info=True)
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/api/strategies', methods=['GET'])
def get_strategies():
    """Get list of strategies and their status"""
    try:
        if not hasattr(trading_system, 'strategy_engine'):
            return jsonify({'success': False, 'message': 'Trading system not initialized'})
            
        strategies = trading_system.strategy_engine.get_strategy_stats()
        return jsonify(strategies)
    
    except Exception as e:
        logger.error(f"Error getting strategies: {e}", exc_info=True)
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/api/strategies/<strategy_name>/enable', methods=['POST'])
def enable_strategy(strategy_name):
    """Enable a specific strategy"""
    try:
        result = trading_system.strategy_engine.enable_strategy(strategy_name)
        
        if result:
            return jsonify({'success': True, 'message': f'Strategy {strategy_name} enabled'})
        else:
            return jsonify({'success': False, 'message': f'Strategy {strategy_name} not found'})
    
    except Exception as e:
        logger.error(f"Error enabling strategy: {e}", exc_info=True)
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/api/strategies/<strategy_name>/disable', methods=['POST'])
def disable_strategy(strategy_name):
    """Disable a specific strategy"""
    try:
        result = trading_system.strategy_engine.disable_strategy(strategy_name)
        
        if result:
            return jsonify({'success': True, 'message': f'Strategy {strategy_name} disabled'})
        else:
            return jsonify({'success': False, 'message': f'Strategy {strategy_name} not found'})
    
    except Exception as e:
        logger.error(f"Error disabling strategy: {e}", exc_info=True)
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/api/positions', methods=['GET'])
def get_positions():
    """Get current positions"""
    try:
        positions = trading_system.position_manager.get_all_positions()
        
        # Convert to serializable format
        serializable_positions = []
        for pos in positions:
            pos_copy = dict(pos)
            for key, value in pos.items():
                if isinstance(value, datetime):
                    pos_copy[key] = value.strftime('%Y-%m-%d %H:%M:%S')
            serializable_positions.append(pos_copy)
            
        return jsonify(serializable_positions)
    
    except Exception as e:
        logger.error(f"Error getting positions: {e}", exc_info=True)
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/api/positions/<position_id>/close', methods=['POST'])
def close_position(position_id):
    """Close a specific position"""
    try:
        result = trading_system.position_manager._close_position(position_id, "Manual close via API")
        
        if result:
            return jsonify({'success': True, 'message': f'Position {position_id} closing'})
        else:
            return jsonify({'success': False, 'message': f'Failed to close position {position_id}'})
    
    except Exception as e:
        logger.error(f"Error closing position: {e}", exc_info=True)
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/api/performance', methods=['GET'])
def get_performance():
    """Get performance metrics"""
    try:
        metrics = trading_system.analytics.get_performance_metrics()
        
        # Convert to serializable format
        serializable_metrics = {}
        for key, value in metrics.items():
            if isinstance(value, (list, dict)):
                # Handle nested structures
                if isinstance(value, list):
                    serializable_metrics[key] = []
                    for item in value:
                        if isinstance(item, dict):
                            item_copy = dict(item)
                            for k, v in item.items():
                                if isinstance(v, datetime):
                                    item_copy[k] = v.strftime('%Y-%m-%d %H:%M:%S')
                            serializable_metrics[key].append(item_copy)
                        else:
                            serializable_metrics[key].append(item)
            else:
                serializable_metrics[key] = value
                
        return jsonify(serializable_metrics)
    
    except Exception as e:
        logger.error(f"Error getting performance: {e}", exc_info=True)
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/api/settings', methods=['GET', 'PUT'])
def manage_settings():
    """Get or update system settings"""
    try:
        if request.method == 'GET':
            # Return current settings
            settings = {
                'max_capital_at_risk': trading_system.risk_manager.max_capital_at_risk * 100,
                'max_position_size': trading_system.risk_manager.max_position_size * 100,
                'daily_loss_limit': trading_system.risk_manager.daily_loss_limit * 100,
                'overnight_limit': trading_system.risk_manager.overnight_limit * 100
            }
            return jsonify(settings)
        else:  # PUT
            # Update settings
            data = request.json
            
            if 'max_capital_at_risk' in data:
                trading_system.risk_manager.max_capital_at_risk = float(data['max_capital_at_risk']) / 100
                
            if 'max_position_size' in data:
                trading_system.risk_manager.max_position_size = float(data['max_position_size']) / 100
                
            if 'daily_loss_limit' in data:
                trading_system.risk_manager.daily_loss_limit = float(data['daily_loss_limit']) / 100
                
            if 'overnight_limit' in data:
                trading_system.risk_manager.overnight_limit = float(data['overnight_limit']) / 100
                
            return jsonify({'success': True, 'message': 'Settings updated'})
    
    except Exception as e:
        logger.error(f"Error managing settings: {e}", exc_info=True)
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/api/quantity', methods=['POST'])
def set_order_quantity():
    """Set order quantity for a strategy"""
    try:
        data = request.json
        
        if not data or 'strategy' not in data or 'quantity' not in data:
            return jsonify({'success': False, 'message': 'Missing required fields'})
            
        strategy_name = data['strategy']
        quantity = int(data['quantity'])
        
        # Find the strategy
        for strategy in trading_system.strategy_engine.strategies:
            if strategy['name'] == strategy_name:
                # Store quantity in strategy parameters
                if 'params' not in strategy:
                    strategy['params'] = {}
                strategy['params']['order_quantity'] = quantity
                
                logger.info(f"Set order quantity for {strategy_name} to {quantity}")
                return jsonify({'success': True, 'message': f'Order quantity set to {quantity} for {strategy_name}'})
        
        return jsonify({'success': False, 'message': f'Strategy {strategy_name} not found'})
    
    except Exception as e:
        logger.error(f"Error setting order quantity: {e}", exc_info=True)
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)