FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir requests

# Copy load test script
COPY load_test.py .

# Make script executable
RUN chmod +x load_test.py

# Default command - run sustained load test
CMD ["python", "load_test.py", "--mode", "sustained", "--duration", "60", "--rate", "10"]