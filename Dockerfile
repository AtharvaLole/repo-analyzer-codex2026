FROM python:3.11-slim

# Install git (required by GitPython for repo cloning)
RUN apt-get update && \
    apt-get install -y --no-install-recommends git && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies from backend directory
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --use-deprecated=legacy-resolver -r requirements.txt

# Copy backend application code
COPY backend/ .

# Create data directories
RUN mkdir -p .data/chroma .data/repos

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
