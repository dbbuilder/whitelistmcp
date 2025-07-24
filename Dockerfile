# Build stage
FROM python:3.10-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Runtime stage
FROM python:3.10-slim

WORKDIR /app

# Create non-root user
RUN useradd -m -u 1000 mcpuser

# Copy installed packages from builder
COPY --from=builder /root/.local /home/mcpuser/.local

# Copy application code
COPY whitelistmcp/ ./whitelistmcp/
COPY setup.py .
COPY README.md .

# Install the application
RUN pip install --no-cache-dir -e .

# Create logs directory
RUN mkdir -p /app/logs && chown mcpuser:mcpuser /app/logs

# Switch to non-root user
USER mcpuser

# Update PATH
ENV PATH=/home/mcpuser/.local/bin:$PATH

# Set Python to run in unbuffered mode
ENV PYTHONUNBUFFERED=1

# Default command
CMD ["python", "-m", "whitelistmcp.main"]