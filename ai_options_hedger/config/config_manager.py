"""
Configuration Manager for Intelligent Options Hedging Engine
Handles configuration loading, validation, and dynamic updates
"""
import os
import yaml
import json
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from cryptography.fernet import Fernet
import aiofiles

logger = logging.getLogger(__name__)

def load_config(config_path: str = None) -> Dict[str, Any]:
    """
    Load configuration from YAML and environment files
    Used by paper trading and other components
    """
    # Default paths
    base_path = Path(__file__).parent
    if not config_path:
        config_path = base_path / "params.yaml"
    
    secrets_path = base_path / "secrets.env"
    
    # Load YAML config
    config = {}
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Failed to load config from {config_path}: {e}")
        config = {}
    
    # Load secrets from .env file
    secrets = {}
    try:
        if secrets_path.exists():
            with open(secrets_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        secrets[key.strip()] = value.strip()
    except Exception as e:
        logger.error(f"Failed to load secrets from {secrets_path}: {e}")
    
    # Merge secrets into config
    config.update(secrets)
    
    return config

@dataclass
class TradingConfig:
    """Trading-specific configuration"""
    max_positions: int = 10
    max_risk_per_trade: float = 0.02  # 2% max risk
    max_daily_loss: float = 0.05  # 5% max daily loss
    position_sizing: str = "fixed"  # fixed, dynamic, kelly
    
    # Capital settings
    initial_capital: float = 1000000.0  # ₹10 Lakh
    max_position_size: float = 0.05  # 5% of capital per position
    risk_free_rate: float = 0.065  # Current RBI rate
    
    # Index-specific settings
    sensex_hedge_premium_diff: float = 90.0  # ₹80-₹100
    nifty_hedge_premium_diff: float = 50.0   # ≤₹50
    
    # Exit rules
    profit_target: float = 0.20  # 20% profit target
    stop_loss: float = 0.15      # 15% stop loss
    trail_percentage: float = 0.05  # 5% trailing stop
    
    # Options-specific (nested dict handling)
    options: dict = None
    
    def __post_init__(self):
        if self.options is None:
            self.options = {}

@dataclass
class RLConfig:
    """Reinforcement Learning configuration"""
    model_type: str = "PPO"  # PPO or DQN
    learning_rate: float = 0.0003
    batch_size: int = 64
    buffer_size: int = 100000
    update_frequency: int = 1000
    save_frequency: int = 10000
    exploration_rate: float = 0.1
    model_path: str = "models/rl_hedge_agent.pkl"

@dataclass
class SignalConfig:
    """Signal evaluation configuration"""
    confidence_threshold: float = 0.75
    confluence_weight: float = 0.3
    pattern_weight: float = 0.25
    volume_weight: float = 0.2
    momentum_weight: float = 0.25
    
    # Signal timeframes
    primary_timeframe: str = "5m"
    confirmation_timeframes: list = None
    
    def __post_init__(self):
        if self.confirmation_timeframes is None:
            self.confirmation_timeframes = ["1m", "15m", "1h"]

@dataclass
class DhanConfig:
    """DhanHQ API configuration"""
    base_url: str = "https://api.dhan.co"
    access_token: Optional[str] = None
    client_id: Optional[str] = None
    rate_limit: int = 1000  # requests per minute
    timeout: int = 10
    
class ConfigManager:
    """Advanced configuration management with encryption and hot-reloading"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.config_file = self.config_dir / "params.yaml"
        self.secrets_file = self.config_dir / "secrets.env"
        self.runtime_config_file = self.config_dir / "runtime.json"
        
        # Configuration objects
        self.trading_config = TradingConfig()
        self.rl_config = RLConfig()
        self.signal_config = SignalConfig()
        self.dhan_config = DhanConfig()
        
        # Runtime state
        self.runtime_config = {}
        self._encryption_key = None
        self._watchers = []
        
        # Setup encryption for sensitive data
        self._setup_encryption()
        
    def _setup_encryption(self):
        """Setup encryption for sensitive configuration data"""
        key_file = self.config_dir / ".key"
        if key_file.exists():
            with open(key_file, "rb") as f:
                self._encryption_key = f.read()
        else:
            self._encryption_key = Fernet.generate_key()
            os.makedirs(self.config_dir, exist_ok=True)
            with open(key_file, "wb") as f:
                f.write(self._encryption_key)
            # Set restrictive permissions
            os.chmod(key_file, 0o600)
        
        self.cipher = Fernet(self._encryption_key)
    
    async def load_config(self):
        """Load configuration from files"""
        try:
            # Load main configuration
            if self.config_file.exists():
                async with aiofiles.open(self.config_file, 'r') as f:
                    content = await f.read()
                    config_data = yaml.safe_load(content)
                    await self._parse_config(config_data)
            else:
                await self._create_default_config()
            
            # Load secrets
            await self._load_secrets()
            
            # Load runtime configuration
            await self._load_runtime_config()
            
            logger.info("✅ Configuration loaded successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to load configuration: {e}")
            raise
    
    async def _parse_config(self, config_data: Dict[str, Any]):
        """Parse configuration data into structured objects"""
        # Trading configuration
        if "trading" in config_data:
            trading_data = config_data["trading"]
            self.trading_config = TradingConfig(**trading_data)
        
        # RL configuration
        if "reinforcement_learning" in config_data:
            rl_data = config_data["reinforcement_learning"]
            self.rl_config = RLConfig(**rl_data)
        
        # Signal configuration
        if "signals" in config_data:
            signal_data = config_data["signals"]
            self.signal_config = SignalConfig(**signal_data)
        
        # DhanHQ configuration
        if "dhan" in config_data:
            dhan_data = config_data["dhan"]
            # Don't include sensitive data here
            self.dhan_config.base_url = dhan_data.get("base_url", self.dhan_config.base_url)
            self.dhan_config.rate_limit = dhan_data.get("rate_limit", self.dhan_config.rate_limit)
            self.dhan_config.timeout = dhan_data.get("timeout", self.dhan_config.timeout)
    
    async def _load_secrets(self):
        """Load encrypted secrets"""
        if not self.secrets_file.exists():
            await self._create_default_secrets()
            return
        
        try:
            async with aiofiles.open(self.secrets_file, 'r') as f:
                content = await f.read()
                
            # Parse environment variables
            for line in content.strip().split('\n'):
                if '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"\'')
                    
                    # Decrypt if needed
                    if value.startswith('ENCRYPTED:'):
                        value = self.cipher.decrypt(value[10:].encode()).decode()
                    
                    # Set in appropriate config
                    if key == 'DHAN_ACCESS_TOKEN':
                        self.dhan_config.access_token = value
                    elif key == 'DHAN_CLIENT_ID':
                        self.dhan_config.client_id = value
                    
                    # Also set as environment variable
                    os.environ[key] = value
                    
        except Exception as e:
            logger.error(f"Failed to load secrets: {e}")
    
    async def _load_runtime_config(self):
        """Load runtime configuration state"""
        if self.runtime_config_file.exists():
            try:
                async with aiofiles.open(self.runtime_config_file, 'r') as f:
                    content = await f.read()
                    self.runtime_config = json.loads(content)
            except Exception as e:
                logger.warning(f"Failed to load runtime config: {e}")
                self.runtime_config = {}
    
    async def _create_default_config(self):
        """Create default configuration file"""
        default_config = {
            "trading": asdict(self.trading_config),
            "reinforcement_learning": asdict(self.rl_config),
            "signals": asdict(self.signal_config),
            "dhan": {
                "base_url": self.dhan_config.base_url,
                "rate_limit": self.dhan_config.rate_limit,
                "timeout": self.dhan_config.timeout
            }
        }
        
        os.makedirs(self.config_dir, exist_ok=True)
        async with aiofiles.open(self.config_file, 'w') as f:
            await f.write(yaml.dump(default_config, default_flow_style=False))
        
        logger.info(f"Created default configuration: {self.config_file}")
    
    async def _create_default_secrets(self):
        """Create default secrets file"""
        default_secrets = """# DhanHQ API Credentials
DHAN_ACCESS_TOKEN=your_access_token_here
DHAN_CLIENT_ID=your_client_id_here

# Notification Settings
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Database Settings
DATABASE_URL=sqlite:///hedge_engine.db

# Email Settings (Optional)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_USER=your_email@gmail.com
EMAIL_PASSWORD=your_app_password
"""
        
        os.makedirs(self.config_dir, exist_ok=True)
        async with aiofiles.open(self.secrets_file, 'w') as f:
            await f.write(default_secrets)
        
        # Set restrictive permissions
        os.chmod(self.secrets_file, 0o600)
        logger.info(f"Created default secrets file: {self.secrets_file}")
    
    async def update_access_key(self, access_token: str):
        """Update DhanHQ access token with encryption"""
        try:
            # Encrypt the token
            encrypted_token = self.cipher.encrypt(access_token.encode()).decode()
            
            # Update in memory
            self.dhan_config.access_token = access_token
            os.environ['DHAN_ACCESS_TOKEN'] = access_token
            
            # Update secrets file
            content = ""
            if self.secrets_file.exists():
                async with aiofiles.open(self.secrets_file, 'r') as f:
                    content = await f.read()
            
            # Replace or add the access token
            lines = content.split('\n')
            token_updated = False
            
            for i, line in enumerate(lines):
                if line.startswith('DHAN_ACCESS_TOKEN='):
                    lines[i] = f'DHAN_ACCESS_TOKEN=ENCRYPTED:{encrypted_token}'
                    token_updated = True
                    break
            
            if not token_updated:
                lines.append(f'DHAN_ACCESS_TOKEN=ENCRYPTED:{encrypted_token}')
            
            # Write back
            async with aiofiles.open(self.secrets_file, 'w') as f:
                await f.write('\n'.join(lines))
            
            logger.info("✅ Access token updated and encrypted")
            
        except Exception as e:
            logger.error(f"❌ Failed to update access token: {e}")
            raise
    
    def get_config(self, section: str = None) -> Any:
        """Get configuration object or section"""
        if section is None:
            return {
                "trading": self.trading_config,
                "rl": self.rl_config,
                "signals": self.signal_config,
                "dhan": self.dhan_config,
                "runtime": self.runtime_config
            }
        
        if section == "trading":
            return self.trading_config
        elif section == "rl":
            return self.rl_config
        elif section == "signals":
            return self.signal_config
        elif section == "dhan":
            return self.dhan_config
        elif section == "runtime":
            return self.runtime_config
        else:
            raise ValueError(f"Unknown configuration section: {section}")
    
    async def update_runtime_config(self, key: str, value: Any):
        """Update runtime configuration"""
        self.runtime_config[key] = value
        
        # Save to file
        try:
            async with aiofiles.open(self.runtime_config_file, 'w') as f:
                await f.write(json.dumps(self.runtime_config, indent=2))
        except Exception as e:
            logger.warning(f"Failed to save runtime config: {e}")
    
    async def validate_config(self) -> bool:
        """Validate current configuration"""
        try:
            # Check trading config
            assert 0 < self.trading_config.max_risk_per_trade <= 0.1, "Risk per trade must be between 0.1% and 10%"
            assert 0 < self.trading_config.max_daily_loss <= 0.2, "Daily loss limit must be between 0.1% and 20%"
            
            # Check DhanHQ config
            if not self.dhan_config.access_token:
                logger.warning("⚠️  DhanHQ access token not configured")
                return False
            
            # Check signal config
            assert 0 < self.signal_config.confidence_threshold <= 1.0, "Confidence threshold must be between 0 and 1"
            
            logger.info("✅ Configuration validation passed")
            return True
            
        except AssertionError as e:
            logger.error(f"❌ Configuration validation failed: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Configuration validation error: {e}")
            return False
