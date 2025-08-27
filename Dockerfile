FROM python:3.11-slim

# Install ImageMagick and WebP codec with security updates
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    imagemagick webp \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# Set Python to unbuffered mode (prints show immediately in logs)
ENV PYTHONUNBUFFERED=1

 # Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App files
WORKDIR /app
COPY watcher.py /app/watcher.py

# Create mount points
RUN mkdir -p /data/input /data/output

# Optional: set sane defaults (override at runtime)
ENV INPUT_DIR=/data/input
ENV OUTPUT_DIR=/data/output
ENV WEBP_QUALITY=100
ENV WEBP_METHOD=4
ENV WEBP_LOSSLESS=false

CMD ["python", "watcher.py"]