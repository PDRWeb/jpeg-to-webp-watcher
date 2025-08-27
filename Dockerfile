FROM python:3.11-slim

# Install ImageMagick and WebP codec
RUN apt-get update && apt-get install -y --no-install-recommends \
    imagemagick webp \
 && rm -rf /var/lib/apt/lists/*

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
ENV WEBP_QUALITY=82
ENV WEBP_METHOD=6
ENV WEBP_LOSSLESS=false

CMD ["python", "watcher.py"]