# Use official Python base image
FROM python:3.12-slim

# Create a non-root user
RUN addgroup --system app && adduser --system --ingroup app appuser

# Set working directory
WORKDIR /app

# Install uv package manager globally
RUN pip install --no-cache-dir uv

# Copy dependency manifests
COPY pyproject.toml uv.lock ./

# Create virtual environment & install production deps
RUN uv venv --python python3.12 .venv \
    && uv sync --frozen --no-dev \
    && rm -rf /root/.cache

# Copy application source
COPY . .

# Set ownership to non-root user
RUN chown -R appuser:app /app

# Switch to non-root
USER appuser

# Expose FastAPI port
EXPOSE 8000

# Start application (default 1 worker, override via NUM_WORKERS env)
CMD ["/bin/sh", "-c", "exec /app/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers ${NUM_WORKERS:-1}"] 