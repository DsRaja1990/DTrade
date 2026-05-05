# Intelligent Options Hedging Engine

A world-class, institutional-grade intelligent options hedging engine for F&O options (Sensex/Nifty) using AI prediction, reinforcement learning, and advanced market microstructure analysis.

## 🎯 Features

### Advanced AI & Machine Learning
- **Deep Reinforcement Learning**: Multi-agent trading system with DQN, PPO, and Actor-Critic algorithms
- **Neuro-Symbolic Intelligence**: Combines neural networks with symbolic reasoning for robust decision making
- **Quantum-Inspired Optimization**: Advanced portfolio optimization using quantum algorithms
- **Self-Evolving Algorithms**: Genetic algorithms that adapt to changing market conditions

### Market Microstructure Analysis
- **Order Book Imbalance Detection**: Real-time analysis of market depth and flow
- **HFT Breakout Detection**: Identifies high-frequency trading patterns and opportunities
- **Market Depth Analytics**: Advanced liquidity and spread analysis
- **Smart Order Flow**: Intelligent order routing and execution

### Risk Management
- **Real-time Risk Assessment**: Continuous monitoring of portfolio risk metrics
- **VaR and Stress Testing**: Monte Carlo simulations and scenario analysis
- **Dynamic Position Sizing**: Kelly criterion and volatility-adjusted sizing
- **Multi-layered Stop Losses**: Portfolio, daily, and individual position stops

### Strategy Engine
- **Auto-Adaptive Strategy Selection**: ML-based strategy selection based on market regime
- **Volatility Event Handling**: Automated detection and trading around earnings and events
- **Signal Confluence**: Multi-source signal aggregation with confidence scoring
- **Options-Specific Strategies**: Delta-neutral, gamma scalping, iron condors, butterflies

### Integration & Monitoring
- **DhanHQ API Integration**: Live market data and order execution
- **Real-time Dashboard**: Web-based monitoring and control interface
- **Multi-channel Notifications**: Email, Telegram, Slack, Discord alerts
- **Comprehensive Logging**: Structured logging with performance tracking

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- DhanHQ trading account
- Minimum 8GB RAM (16GB recommended)
- Stable internet connection

### Installation

1. **Clone the repository:**
```bash
git clone https://github.com/yourusername/intelligent-options-hedger.git
cd intelligent-options-hedger
```

2. **Install dependencies:**
```bash
# Windows
.\start.bat --validate-config

# Linux/Mac
chmod +x start.sh
./start.sh --validate-config
```

3. **Configure the engine:**
Edit `config/config.yaml` with your settings:
```yaml
brokers:
  dhan:
    enabled: true
    client_id: "your_dhan_client_id"
    access_token: "your_dhan_access_token"

notifications:
  telegram:
    bot_token: "your_telegram_bot_token"
    chat_ids: ["your_chat_id"]
```

4. **Start the engine:**
```bash
# Paper trading mode (recommended for first run)
python start.py --paper-trading

# Live trading mode
python start.py

# Dashboard only
python start.py --dashboard-only
```

5. **Access the dashboard:**
Open http://localhost:8080 in your browser

## 📋 Configuration

### Broker Setup
The engine supports multiple brokers with DhanHQ as the primary:

```yaml
brokers:
  dhan:
    enabled: true
    primary: true
    client_id: "your_client_id"
    access_token: "your_access_token"
  
  mock:
    enabled: true  # For testing
    primary: false
```

### Risk Management
Configure risk parameters according to your risk tolerance:

```yaml
risk_management:
  max_portfolio_risk: 0.1  # 10% VaR
  max_drawdown: 0.15       # 15% max drawdown
  leverage_limit: 3.0      # 3x leverage
  
  stop_loss:
    portfolio_stop_loss: 0.1   # 10%
    daily_stop_loss: 0.05      # 5%
    individual_stop_loss: 0.03 # 3%
```

### AI Configuration
Fine-tune AI components:

```yaml
ai_engine:
  reinforcement_learning:
    algorithm: "PPO"
    learning_rate: 0.0001
    batch_size: 64
    
  multi_agent:
    agents:
      - name: "DirectionalAgent"
        allocation: 0.4
      - name: "MeanReversionAgent"
        allocation: 0.3
      - name: "VolatilityAgent"
        allocation: 0.3
```

## 🏗️ Architecture

### Component Overview
```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend Dashboard                      │
├─────────────────────────────────────────────────────────────┤
│                      Main Engine                           │
├─────────────────────────────────────────────────────────────┤
│  Signal Engine  │  Strategy Engine  │  Risk Management    │
├─────────────────────────────────────────────────────────────┤
│     AI Engine     │  Microstructure  │  Trade Execution   │
├─────────────────────────────────────────────────────────────┤
│              Data Ingestion & Broker APIs                  │
└─────────────────────────────────────────────────────────────┘
```

### Directory Structure
```
intelligent-options-hedger/
├── config/                 # Configuration files
├── data_ingestion/         # Market data connectors
├── microstructure/         # Market microstructure analysis
├── ai_engine/             # AI and ML components
├── signals/               # Signal generation
├── strategies/            # Trading strategies
├── evaluation/            # Performance monitoring
├── utils/                 # Utilities (logging, notifications)
├── frontend/              # Dashboard interface
├── logs/                  # Log files
├── data/                  # Data storage
└── models/                # Trained ML models
```

## 🔧 Usage Examples

### Basic Trading
```python
# Start with paper trading
python start.py --paper-trading --debug

# Live trading with custom config
python start.py --config custom_config.yaml

# Test mode with mock data
python start.py --test-mode
```

### Dashboard Features
- **Real-time P&L**: Live portfolio performance
- **Risk Metrics**: VaR, drawdown, exposure analysis
- **Signal Analysis**: Current signals and confidence levels
- **Trade History**: Detailed execution logs
- **Model Performance**: AI model accuracy and predictions
- **Emergency Controls**: Pause/resume trading, emergency stop

### API Endpoints
```bash
# Get system status
curl http://localhost:8080/api/system/status

# Get performance summary
curl http://localhost:8080/api/performance/summary

# Emergency stop
curl -X POST http://localhost:8080/api/control/emergency_stop
```

## 📊 Performance Monitoring

### Key Metrics
- **Sharpe Ratio**: Risk-adjusted returns
- **Maximum Drawdown**: Worst peak-to-trough decline
- **Win Rate**: Percentage of profitable trades
- **Profit Factor**: Gross profit / gross loss
- **Calmar Ratio**: Annual return / max drawdown

### Risk Monitoring
- **Value at Risk (VaR)**: 95% confidence portfolio risk
- **Stress Testing**: Performance under extreme scenarios
- **Correlation Analysis**: Portfolio diversification metrics
- **Volatility Tracking**: Realized vs implied volatility

## 🚨 Risk Warnings

### Important Disclaimers
- **This is experimental software**: Use at your own risk
- **Start with paper trading**: Test thoroughly before live trading
- **Monitor positions closely**: Automated systems can malfunction
- **Set appropriate risk limits**: Never risk more than you can afford to lose
- **Market risks apply**: Past performance doesn't guarantee future results

### Recommended Practices
1. **Start Small**: Begin with minimal position sizes
2. **Paper Trade First**: Test all strategies in simulation
3. **Monitor Continuously**: Keep an eye on the dashboard
4. **Set Conservative Limits**: Use lower risk parameters initially
5. **Have Backup Plans**: Manual override capabilities

## 🛠️ Development

### Adding New Strategies
```python
# Create new strategy in strategies/
class MyCustomStrategy(BaseStrategy):
    async def generate_signals(self, market_data):
        # Your strategy logic
        return signals
    
    async def calculate_position_size(self, signal):
        # Position sizing logic
        return size
```

### Extending AI Components
```python
# Add new AI model in ai_engine/
class MyMLModel(BaseAIModel):
    async def train(self, data):
        # Training logic
        pass
    
    async def predict(self, features):
        # Prediction logic
        return prediction
```

### Custom Indicators
```python
# Add technical indicators in signals/
class MyIndicator:
    def calculate(self, price_data):
        # Indicator calculation
        return indicator_values
```

## 📈 Advanced Features

### Multi-Asset Support
- **Index Options**: Nifty, Bank Nifty, Sensex
- **Stock Options**: Individual stock options
- **Futures**: Index and stock futures
- **Cross-Asset Strategies**: Multi-instrument hedging

### Advanced AI Features
- **Transfer Learning**: Adapt models to new instruments
- **Ensemble Methods**: Combine multiple models
- **Online Learning**: Continuous model updates
- **Adversarial Training**: Robust model training

### Institutional Features
- **Multi-Broker Support**: Risk distribution across brokers
- **Compliance Monitoring**: Regulatory compliance checks
- **Audit Trails**: Comprehensive trade logging
- **Performance Attribution**: Strategy-level performance analysis

## 🔍 Troubleshooting

### Common Issues

**Engine won't start:**
```bash
# Check configuration
python start.py --validate-config

# Check logs
tail -f logs/hedging_engine.log
```

**Dashboard not accessible:**
- Check if port 8080 is available
- Verify firewall settings
- Check dashboard configuration in config.yaml

**Broker connection issues:**
- Verify API credentials
- Check network connectivity
- Review broker-specific logs

**High memory usage:**
- Reduce AI model complexity
- Adjust data retention settings
- Monitor for memory leaks

### Getting Help
1. **Check Logs**: Look in `logs/` directory
2. **Review Configuration**: Validate config.yaml
3. **Test Components**: Use individual component tests
4. **Community Support**: GitHub issues and discussions

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

This software is for educational and research purposes. The authors are not responsible for any financial losses incurred through the use of this software. Trading in financial markets involves substantial risk and is not suitable for all investors. Past performance is not indicative of future results.

## 🤝 Contributing

Contributions are welcome! Please read our [Contributing Guidelines](CONTRIBUTING.md) for details on how to submit pull requests, report issues, and contribute to the project.

## 📞 Support

- **Documentation**: [Wiki](https://github.com/yourusername/intelligent-options-hedger/wiki)
- **Issues**: [GitHub Issues](https://github.com/yourusername/intelligent-options-hedger/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/intelligent-options-hedger/discussions)
- **Email**: support@yourcompany.com

---

**Built with ❤️ for the trading community**
