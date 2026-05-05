"""
Centralized Configuration for Trading Services
Stores all API keys, tokens, and service configurations
"""

import os
import json
from typing import Dict, Optional
from datetime import datetime

class TradingConfig:
    """Centralized configuration manager for all trading services"""
    
    CONFIG_FILE = "config.json"
    
    def __init__(self):
        self.config = self._load_config()
    
    def _load_config(self) -> Dict:
        """Load configuration from file or create default"""
        if os.path.exists(self.CONFIG_FILE):
            try:
                with open(self.CONFIG_FILE, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading config: {e}, using defaults")
        
        # Default configuration
        return {
            "dhan_api": {
                "client_id": os.environ.get("DHAN_CLIENT_ID", "1101317572"),
                "access_token": os.environ.get("DHAN_ACCESS_TOKEN", 
                    "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzY0MDA3NDkxLCJpYXQiOjE3NjM5MjEwOTEsInRva2VuQ29uc3VtZXJUeXBlIjoiU0VMRiIsIndlYmhvb2tVcmwiOiIiLCJkaGFuQ2xpZW50SWQiOiIxMTAxMzE3NTcyIn0.7on018K2XTUZunTh9noYa_LQBZLW8aDQ-CTqr6TNvFooqo16uFqAxSvulIesnzcGdK2c3g6dWV_djIugFs82EA"),
                "last_updated": datetime.now().isoformat()
            },
            "gemini_api": {
                "tier_1_2": {
                    "api_key": os.environ.get("TIER_1_2_API_KEY", "AIzaSyDy94t-9c8M1HO7x95y-zvoXto9Y-oeODo"),
                    "project": "projects/1050246201472",
                    "project_number": "1050246201472",
                    "name": "Generative Language API Key",
                    "usage": "Stock Screener + Strategy Engine (Free Version)",
                    "model": "gemini-2.5-flash"
                },
                "tier_3": {
                    "api_key": os.environ.get("TIER_3_API_KEY", "AIzaSyA7FfMquiCuzLkbUryGw_7woTQ4KQngFG0"),
                    "project": "projects/277222362233",
                    "project_number": "277222362233",
                    "name": "Dtrade - Gemini 3 Pro",
                    "usage": "Ultimate Prediction - Price targets, win probability (Paid Version)",
                    "model": "gemini-3-pro"
                },
                "last_updated": datetime.now().isoformat()
            },
            "service_config": {
                "gemini_trade_service_port": 8080,
                "equity_hv_service_port": 8081,
                "index_scalping_service_port": 8082,
                "intelligent_options_hedger_port": 8083
            },
            "last_modified": datetime.now().isoformat(),
            "version": "1.0"
        }
    
    def save_config(self) -> bool:
        """Save current configuration to file"""
        try:
            self.config["last_modified"] = datetime.now().isoformat()
            with open(self.CONFIG_FILE, 'w') as f:
                json.dump(self.config, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False
    
    def get_dhan_client_id(self) -> str:
        """Get Dhan client ID"""
        return self.config["dhan_api"]["client_id"]
    
    def get_dhan_access_token(self) -> str:
        """Get Dhan access token"""
        return self.config["dhan_api"]["access_token"]
    
    def get_gemini_tier_1_2_key(self) -> str:
        """Get Gemini API key for Tier 1 & 2"""
        return self.config["gemini_api"]["tier_1_2"]["api_key"]
    
    def get_gemini_tier_3_key(self) -> str:
        """Get Gemini API key for Tier 3"""
        return self.config["gemini_api"]["tier_3"]["api_key"]
    
    def update_dhan_credentials(self, client_id: Optional[str] = None, 
                               access_token: Optional[str] = None) -> bool:
        """Update Dhan API credentials"""
        if client_id:
            self.config["dhan_api"]["client_id"] = client_id
        if access_token:
            self.config["dhan_api"]["access_token"] = access_token
        self.config["dhan_api"]["last_updated"] = datetime.now().isoformat()
        return self.save_config()
    
    def update_gemini_keys(self, tier_1_2_key: Optional[str] = None,
                          tier_3_key: Optional[str] = None) -> bool:
        """Update Gemini API keys"""
        if tier_1_2_key:
            self.config["gemini_api"]["tier_1_2"]["api_key"] = tier_1_2_key
        if tier_3_key:
            self.config["gemini_api"]["tier_3"]["api_key"] = tier_3_key
        self.config["gemini_api"]["last_updated"] = datetime.now().isoformat()
        return self.save_config()
    
    def get_all_config(self) -> Dict:
        """Get full configuration (masks sensitive data)"""
        config_copy = json.loads(json.dumps(self.config))
        
        # Mask sensitive data
        if "access_token" in config_copy["dhan_api"]:
            token = config_copy["dhan_api"]["access_token"]
            config_copy["dhan_api"]["access_token"] = token[:20] + "..." + token[-20:] if len(token) > 40 else "***"
        
        if "api_key" in config_copy["gemini_api"]["tier_1_2"]:
            key = config_copy["gemini_api"]["tier_1_2"]["api_key"]
            config_copy["gemini_api"]["tier_1_2"]["api_key"] = key[:10] + "..." + key[-10:] if len(key) > 20 else "***"
        
        if "api_key" in config_copy["gemini_api"]["tier_3"]:
            key = config_copy["gemini_api"]["tier_3"]["api_key"]
            config_copy["gemini_api"]["tier_3"]["api_key"] = key[:10] + "..." + key[-10:] if len(key) > 20 else "***"
        
        return config_copy
    
    def reload_config(self) -> bool:
        """Reload configuration from file"""
        try:
            self.config = self._load_config()
            return True
        except Exception as e:
            print(f"Error reloading config: {e}")
            return False

# Global configuration instance
trading_config = TradingConfig()

# Convenience functions for backward compatibility
def get_dhan_client_id() -> str:
    return trading_config.get_dhan_client_id()

def get_dhan_access_token() -> str:
    return trading_config.get_dhan_access_token()

def get_gemini_tier_1_2_key() -> str:
    return trading_config.get_gemini_tier_1_2_key()

def get_gemini_tier_3_key() -> str:
    return trading_config.get_gemini_tier_3_key()
