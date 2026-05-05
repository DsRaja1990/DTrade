# Equity HV Service Startup Script
$servicePath = "c:\Users\Dhanasimmaraja\Documents\TradeApp\DTrade\equity_hv_service"
Set-Location $servicePath
$env:PYTHONPATH = $servicePath
& "$servicePath\venv\Scripts\python.exe" -m uvicorn equity_hv_service:app --host 127.0.0.1 --port 5080
