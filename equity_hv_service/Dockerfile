# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV EQUITY_HV_HOST=0.0.0.0
ENV EQUITY_HV_PORT=8003
ENV EQUITY_HV_AUTO_START=true
ENV EQUITY_HV_EXECUTION_MODE=paper

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p logs data config

# Expose port
EXPOSE 8003

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8003/health')" || exit 1

# Run the application
CMD ["python", "run_service.py"]
