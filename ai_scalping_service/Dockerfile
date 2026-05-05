# Index Scalping Strategy Service
# High-frequency options scalping for NIFTY 50 and SENSEX

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV INDEX_SCALPING_PORT=8003
ENV INDEX_SCALPING_HOST=0.0.0.0

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p logs data

# Create non-root user for security
RUN useradd -m -u 1000 scalping && \
    chown -R scalping:scalping /app

USER scalping

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:${INDEX_SCALPING_PORT}/health || exit 1

# Expose port
EXPOSE ${INDEX_SCALPING_PORT}

# Start the service
CMD ["python", "index_scalping_service.py"]
