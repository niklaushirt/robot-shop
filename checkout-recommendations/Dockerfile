FROM python:3.11-slim

LABEL service="checkout-recommendations"
LABEL description="AI-powered checkout recommendations with memory leak demo"
LABEL memory_leak="unbounded_cache"

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY server.py .
COPY mcp_server.py .

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=10s --timeout=10s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8080/health')" || exit 1

# Run application
CMD ["python", "server.py"]