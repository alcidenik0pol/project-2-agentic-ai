FROM python:3.11-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project
COPY . .

# Expose port
EXPOSE 8901

# Start FastAPI server
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8901"]
