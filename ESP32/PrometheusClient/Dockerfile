# Base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set timezone
ENV TZ=Asia/Kolkata

# Copy requirements first for caching
COPY requirements.txt .

# Install dependencies
RUN apt-get update && \
    apt-get install -y tzdata curl && \
    pip install --no-cache-dir -r requirements.txt && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy application code
COPY espclient.py .

# Environment variables
ENV ESP32_IP="192.168.0.51" \
    PORT="8700" \
    INTERVAL="5"

# Expose port
EXPOSE 8700

# Healthcheck
HEALTHCHECK --interval=30s --timeout=3s \
    CMD curl -f http://localhost:${PORT}/metrics || exit 1

# Run application
CMD ["python", "espclient.py"]