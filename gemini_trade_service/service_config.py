"""
Gemini Trade Service Configuration
Centralized configuration for API keys, tokens, and service settings

3-TIER ARCHITECTURE:
- Tier 1: Gemini 2.0 Flash-Lite - Data Preparation & Technicals (fast, cheap)
- Tier 2: Gemini 2.5 Flash - Contextual Synthesis & Strategy (balanced)
- Tier 3: Gemini 3 Pro (PAID) - Predictive Modeling & Strategy (BEST MODEL)
"""

from dataclasses import dataclass, field
from typing import Dict, Any
from datetime import datetime
import json
import os

CONFIG_FILE_PATH = os.path.join(os.path.dirname(__file__), "service_config.json")

@dataclass
class GeminiTradeConfig:
    """Configuration for Gemini Trade Service - 3-Tier Predictive Architecture"""
    
    # Dhan API Configuration
    dhan_client_id: str = "1101317572"
    dhan_access_token: str = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzY2MjEyMzAxLCJpYXQiOjE3NjYxMjU5MDEsInRva2VuQ29uc3VtZXJUeXBlIjoiU0VMRiIsIndlYmhvb2tVcmwiOiIiLCJkaGFuQ2xpZW50SWQiOiIxMTAxMzE3NTcyIn0.oTZr9N5p6wj8givgxWSwctGF8SnYVJtXY2aBw7lOwJccnBQmyQhAGAo_07L3MZspj7IedKZe5e0IytO6cmPxJQ"
    dhan_base_url: str = "https://api.dhan.co"
    
    # ========================================================================
    # TIER 1: Data Preparation (The Clean Up Crew)
    # Model: Gemini 2.5 Flash-Lite - Fast, cheap, data cleaning only (10 RPM, 250K TPM)
    # Responsibility: Collect 50 Nifty stocks, calculate technicals, NO sentiment
    # ========================================================================
    gemini_tier_1_api_key: str = "AIzaSyDy94t-9c8M1HO7x95y-zvoXto9Y-oeODo"
    gemini_tier_1_project: str = "projects/1050246201472"
    gemini_tier_1_project_number: str = "1050246201472"
    gemini_tier_1_name: str = "Tier 1 - Data Engine"
    gemini_tier_1_model: str = "gemini-2.5-flash-lite"  # Fast, lightweight model (10 RPM)
    gemini_tier_1_usage: str = "Data Preparation & Technicals - 50 Nifty stocks, RSI, VWAP"
    gemini_tier_1_temperature: float = 0.1  # Low temperature for factual data
    
    # ========================================================================
    # TIER 2: Contextual Synthesis (The Strategist)  
    # Model: Gemini 2.5 Flash - Balanced speed and capability (5 RPM, 250K TPM)
    # Responsibility: Options Chain, VIX, Sentiment, News, FII/DII, Trade Proposal
    # ========================================================================
    gemini_tier_2_api_key: str = "AIzaSyDy94t-9c8M1HO7x95y-zvoXto9Y-oeODo"
    gemini_tier_2_project: str = "projects/1050246201472"
    gemini_tier_2_project_number: str = "1050246201472"
    gemini_tier_2_name: str = "Tier 2 - Strategy Engine"
    gemini_tier_2_model: str = "gemini-2.5-flash"  # Balanced model for synthesis (5 RPM)
    gemini_tier_2_usage: str = "Contextual Synthesis - Options, VIX, Sentiment, Trade Proposal"
    gemini_tier_2_temperature: float = 0.3  # Moderate temperature for analysis
    
    # ========================================================================
    # TIER 3: Ultimate Prediction Engine (The Oracle)
    # Model: Gemini 3 Pro - MOST POWERFUL AI MODEL FOR TRADING
    # Capabilities:
    #   - Advanced reasoning with 2M context window
    #   - Superior pattern recognition in market data
    #   - Multi-step logical inference for price prediction
    #   - Enhanced understanding of market microstructure
    # Responsibility: 
    #   - Precise price target prediction with confidence intervals
    #   - Optimal entry/exit timing with market regime detection
    #   - Stop-loss and target levels with risk-adjusted optimization
    #   - Hold duration prediction based on volatility and momentum
    #   - Final trade validation with win probability assessment
    # ========================================================================
    gemini_tier_3_api_key: str = "AIzaSyA7FfMquiCuzLkbUryGw_7woTQ4KQngFG0"
    gemini_tier_3_project: str = "projects/277222362233"
    gemini_tier_3_project_number: str = "277222362233"
    gemini_tier_3_name: str = "Tier 3 - Ultimate Oracle (Gemini 3 Pro)"
    gemini_tier_3_model: str = "gemini-3-pro"  # ULTIMATE: Gemini 3 Pro - highest reasoning capability
    gemini_tier_3_usage: str = "Ultimate Prediction - Price targets, win probability, risk optimization (PAID TIER)"
    gemini_tier_3_temperature: float = 0.15  # Lower temperature for precise, deterministic predictions
    
    # Tier 3 Advanced Settings for Maximum Win Rate
    gemini_tier_3_max_tokens: int = 8192  # Allow detailed analysis
    gemini_tier_3_top_p: float = 0.9  # Focused but not too narrow
    gemini_tier_3_top_k: int = 40  # Consider top 40 tokens
    
    # Legacy compatibility (keep for backward compat)
    gemini_tier_1_2_api_key: str = "AIzaSyDy94t-9c8M1HO7x95y-zvoXto9Y-oeODo"
    gemini_tier_1_2_project: str = "projects/1050246201472"
    gemini_tier_1_2_project_number: str = "1050246201472"
    gemini_tier_1_2_name: str = "Generative Language API Key"
    gemini_tier_1_2_model: str = "gemini-2.5-flash"
    gemini_tier_1_2_usage: str = "Legacy: Stock Screener + Strategy Engine"
    
    # Service Configuration
    service_port: int = 8080
    debug_mode: bool = True
    log_level: str = "INFO"
    
    # Cache Settings
    tier_1_cache_duration: int = 60  # seconds
    tier_2_cache_duration: int = 300  # seconds
    
    # Metadata
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())
    version: str = "1.0.0"
    
    # ========================================================================
    # Property Accessors for 3-Tier Architecture
    # ========================================================================
    @property
    def tier_1_api_key(self) -> str:
        """Get Tier 1 API key"""
        return self.gemini_tier_1_api_key
    
    @property
    def tier_2_api_key(self) -> str:
        """Get Tier 2 API key"""
        return self.gemini_tier_2_api_key
    
    @property
    def tier_3_api_key(self) -> str:
        """Get Tier 3 API key"""
        return self.gemini_tier_3_api_key
    
    @property
    def tier_1_model(self) -> str:
        """Get Tier 1 model name"""
        return self.gemini_tier_1_model
    
    @property
    def tier_2_model(self) -> str:
        """Get Tier 2 model name"""
        return self.gemini_tier_2_model
    
    @property
    def tier_3_model(self) -> str:
        """Get Tier 3 model name"""
        return self.gemini_tier_3_model
    
    @property
    def tier_1_temperature(self) -> float:
        """Get Tier 1 temperature"""
        return self.gemini_tier_1_temperature
    
    @property
    def tier_2_temperature(self) -> float:
        """Get Tier 2 temperature"""
        return self.gemini_tier_2_temperature
    
    @property
    def tier_3_temperature(self) -> float:
        """Get Tier 3 temperature"""
        return self.gemini_tier_3_temperature
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary - 3-Tier Architecture"""
        return {
            "dhan_api": {
                "client_id": self.dhan_client_id,
                "access_token": self.dhan_access_token,
                "base_url": self.dhan_base_url
            },
            "gemini_api": {
                "tier_1": {
                    "api_key": self.gemini_tier_1_api_key,
                    "project": self.gemini_tier_1_project,
                    "project_number": self.gemini_tier_1_project_number,
                    "name": self.gemini_tier_1_name,
                    "model": self.gemini_tier_1_model,
                    "usage": self.gemini_tier_1_usage,
                    "temperature": self.gemini_tier_1_temperature
                },
                "tier_2": {
                    "api_key": self.gemini_tier_2_api_key,
                    "project": self.gemini_tier_2_project,
                    "project_number": self.gemini_tier_2_project_number,
                    "name": self.gemini_tier_2_name,
                    "model": self.gemini_tier_2_model,
                    "usage": self.gemini_tier_2_usage,
                    "temperature": self.gemini_tier_2_temperature
                },
                "tier_3": {
                    "api_key": self.gemini_tier_3_api_key,
                    "project": self.gemini_tier_3_project,
                    "project_number": self.gemini_tier_3_project_number,
                    "name": self.gemini_tier_3_name,
                    "model": self.gemini_tier_3_model,
                    "usage": self.gemini_tier_3_usage,
                    "temperature": self.gemini_tier_3_temperature
                },
                "tier_1_2": {
                    "api_key": self.gemini_tier_1_2_api_key,
                    "project": self.gemini_tier_1_2_project,
                    "project_number": self.gemini_tier_1_2_project_number,
                    "name": self.gemini_tier_1_2_name,
                    "model": self.gemini_tier_1_2_model,
                    "usage": self.gemini_tier_1_2_usage
                }
            },
            "service": {
                "port": self.service_port,
                "debug_mode": self.debug_mode,
                "log_level": self.log_level
            },
            "cache": {
                "tier_1_duration": self.tier_1_cache_duration,
                "tier_2_duration": self.tier_2_cache_duration
            },
            "metadata": {
                "last_updated": self.last_updated,
                "version": self.version
            }
        }
    
    def to_dict_masked(self) -> Dict[str, Any]:
        """Convert config to dictionary with sensitive data masked"""
        config = self.to_dict()
        
        # Mask Dhan token
        token = config["dhan_api"]["access_token"]
        config["dhan_api"]["access_token"] = token[:20] + "..." + token[-20:] if len(token) > 40 else "***"
        
        # Mask Gemini API keys
        tier_1_2_key = config["gemini_api"]["tier_1_2"]["api_key"]
        config["gemini_api"]["tier_1_2"]["api_key"] = tier_1_2_key[:10] + "..." + tier_1_2_key[-10:] if len(tier_1_2_key) > 20 else "***"
        
        tier_3_key = config["gemini_api"]["tier_3"]["api_key"]
        config["gemini_api"]["tier_3"]["api_key"] = tier_3_key[:10] + "..." + tier_3_key[-10:] if len(tier_3_key) > 20 else "***"
        
        return config
    
    def save_to_file(self) -> bool:
        """Save configuration to JSON file"""
        try:
            self.last_updated = datetime.now().isoformat()
            with open(CONFIG_FILE_PATH, 'w') as f:
                json.dump(self.to_dict(), f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False
    
    @classmethod
    def load_from_file(cls) -> 'GeminiTradeConfig':
        """Load configuration from JSON file"""
        try:
            if os.path.exists(CONFIG_FILE_PATH):
                with open(CONFIG_FILE_PATH, 'r') as f:
                    data = json.load(f)
                
                # Extract values from nested structure
                return cls(
                    dhan_client_id=data.get('dhan_api', {}).get('client_id', cls.dhan_client_id),
                    dhan_access_token=data.get('dhan_api', {}).get('access_token', cls.dhan_access_token),
                    dhan_base_url=data.get('dhan_api', {}).get('base_url', cls.dhan_base_url),
                    gemini_tier_1_2_api_key=data.get('gemini_api', {}).get('tier_1_2', {}).get('api_key', cls.gemini_tier_1_2_api_key),
                    gemini_tier_1_2_project=data.get('gemini_api', {}).get('tier_1_2', {}).get('project', cls.gemini_tier_1_2_project),
                    gemini_tier_1_2_project_number=data.get('gemini_api', {}).get('tier_1_2', {}).get('project_number', cls.gemini_tier_1_2_project_number),
                    gemini_tier_1_2_name=data.get('gemini_api', {}).get('tier_1_2', {}).get('name', cls.gemini_tier_1_2_name),
                    gemini_tier_1_2_model=data.get('gemini_api', {}).get('tier_1_2', {}).get('model', cls.gemini_tier_1_2_model),
                    gemini_tier_1_2_usage=data.get('gemini_api', {}).get('tier_1_2', {}).get('usage', cls.gemini_tier_1_2_usage),
                    gemini_tier_3_api_key=data.get('gemini_api', {}).get('tier_3', {}).get('api_key', cls.gemini_tier_3_api_key),
                    gemini_tier_3_project=data.get('gemini_api', {}).get('tier_3', {}).get('project', cls.gemini_tier_3_project),
                    gemini_tier_3_project_number=data.get('gemini_api', {}).get('tier_3', {}).get('project_number', cls.gemini_tier_3_project_number),
                    gemini_tier_3_name=data.get('gemini_api', {}).get('tier_3', {}).get('name', cls.gemini_tier_3_name),
                    gemini_tier_3_model=data.get('gemini_api', {}).get('tier_3', {}).get('model', cls.gemini_tier_3_model),
                    gemini_tier_3_usage=data.get('gemini_api', {}).get('tier_3', {}).get('usage', cls.gemini_tier_3_usage),
                    service_port=data.get('service', {}).get('port', cls.service_port),
                    debug_mode=data.get('service', {}).get('debug_mode', cls.debug_mode),
                    log_level=data.get('service', {}).get('log_level', cls.log_level),
                    tier_1_cache_duration=data.get('cache', {}).get('tier_1_duration', cls.tier_1_cache_duration),
                    tier_2_cache_duration=data.get('cache', {}).get('tier_2_duration', cls.tier_2_cache_duration),
                    last_updated=data.get('metadata', {}).get('last_updated', datetime.now().isoformat()),
                    version=data.get('metadata', {}).get('version', cls.version)
                )
        except Exception as e:
            print(f"Error loading config from file: {e}")
        
        # Return default config if load fails
        return cls()
    
    def update_dhan_credentials(self, client_id: str = None, access_token: str = None) -> bool:
        """Update Dhan API credentials"""
        if client_id:
            self.dhan_client_id = client_id
        if access_token:
            self.dhan_access_token = access_token
        return self.save_to_file()
    
    def update_gemini_keys(self, tier_1_2_key: str = None, tier_3_key: str = None) -> bool:
        """Update Gemini API keys"""
        if tier_1_2_key:
            self.gemini_tier_1_2_api_key = tier_1_2_key
        if tier_3_key:
            self.gemini_tier_3_api_key = tier_3_key
        return self.save_to_file()


# Global configuration instance
try:
    # Try to load from file first
    service_config = GeminiTradeConfig.load_from_file()
except Exception:
    # Fallback to default configuration
    service_config = GeminiTradeConfig()

# Save default config on first run if file doesn't exist
if not os.path.exists(CONFIG_FILE_PATH):
    service_config.save_to_file()
