FROM python:3.10-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY audio_server.py .
COPY audio_AI.py .

CMD ["python", "audio_server.py"]