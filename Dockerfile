FROM python:3.11-slim

# Install system dependencies for audio DSP, WebSockets, and build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ffmpeg \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Set non-root user required by Hugging Face Spaces & security best practices
RUN useradd -m -u 1000 user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1

# Copy dependency list first for efficient Docker layer caching
COPY --chown=user:user agent/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r ./requirements.txt

# Copy agent code
COPY --chown=user:user agent/ ./agent/

# Set workdir to agent folder
WORKDIR /app/agent

# Switch to non-root user
USER user

# Expose port 10000 for Render / cloud healthcheck & metrics
EXPOSE 10000
ENV PORT=10000

# Run worker in production mode
CMD ["python", "main.py", "start"]

